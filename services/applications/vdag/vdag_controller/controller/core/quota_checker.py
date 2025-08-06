import os
import logging
import time
from threading import Lock
import redis
from flask import Flask, jsonify, request

from .schema import vDAGObject
from .policy_sandbox import LocalPolicyEvaluator


class QuotaManagement:
    def __init__(self, redis_host="localhost", redis_port=6379, redis_db=0, quota_ttl=None):
        self._lock = Lock()
        self.quota_ttl = quota_ttl
        self.in_memory_quota = {}  # session_id -> (value, expiry_time or None)

        try:
            self.redis_client = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Connected to Redis for quota management.")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            self.redis_client = None

    def _is_expired(self, expiry_time):
        return expiry_time is not None and time.time() > expiry_time

    def _get_in_memory(self, session_id):
        entry = self.in_memory_quota.get(session_id)
        if not entry:
            return 0
        value, expiry_time = entry
        if self._is_expired(expiry_time):
            del self.in_memory_quota[session_id]
            return 0
        return value

    def increment(self, session_id: str, amount: int = 1) -> int:
        if amount < 0:
            raise ValueError("Increment amount cannot be negative.")

        with self._lock:
            if self.redis_client:
                try:
                    new_quota = self.redis_client.incrby(session_id, amount)
                    if self.quota_ttl is not None:
                        self.redis_client.expire(session_id, self.quota_ttl)
                    logger.debug(f"Incremented quota for {session_id} to {new_quota}")
                    return new_quota
                except redis.RedisError as e:
                    logger.error(f"Redis error in increment: {e}")

            # In-memory fallback
            value = self._get_in_memory(session_id)
            new_value = value + amount
            expiry_time = time.time() + self.quota_ttl if self.quota_ttl is not None else None
            self.in_memory_quota[session_id] = (new_value, expiry_time)
            logger.debug(f"[Fallback] Incremented quota for {session_id} to {new_value}")
            return new_value

    def get(self, session_id: str) -> int:
        with self._lock:
            if self.redis_client:
                try:
                    value = self.redis_client.get(session_id)
                    return int(value) if value else 0
                except redis.RedisError as e:
                    logger.error(f"Redis error in get: {e}")

            return self._get_in_memory(session_id)

    def reset(self, session_id: str) -> None:
        with self._lock:
            if self.redis_client:
                try:
                    self.redis_client.set(session_id, 0)
                    if self.quota_ttl is not None:
                        self.redis_client.expire(session_id, self.quota_ttl)
                    return
                except redis.RedisError as e:
                    logger.error(f"Redis error in reset: {e}")

            expiry_time = time.time() + self.quota_ttl if self.quota_ttl is not None else None
            self.in_memory_quota[session_id] = (0, expiry_time)

    def clean(self) -> None:
        with self._lock:
            if self.redis_client:
                try:
                    self.redis_client.flushdb()
                    logger.info("All quotas cleared from Redis.")
                    return
                except redis.RedisError as e:
                    logger.error(f"Redis error in clean: {e}")

            self.in_memory_quota.clear()
            logger.info("[Fallback] All quotas cleared from in-memory store.")

    def remove(self, session_id: str) -> None:
        with self._lock:
            if self.redis_client:
                try:
                    self.redis_client.delete(session_id)
                    return
                except redis.RedisError as e:
                    logger.error(f"Redis error in remove: {e}")

            self.in_memory_quota.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        with self._lock:
            if self.redis_client:
                try:
                    return self.redis_client.exists(session_id) > 0
                except redis.RedisError as e:
                    logger.error(f"Redis error in exists: {e}")

            entry = self.in_memory_quota.get(session_id)
            if not entry:
                return False
            _, expiry_time = entry
            if self._is_expired(expiry_time):
                del self.in_memory_quota[session_id]
                return False
            return True


logger = logging.getLogger(__name__)


class QuotaManager:
    def __init__(self, vdag_info: vDAGObject, custom_init_data={}) -> None:
        self.vdag_info = vdag_info
        controller = self.vdag_info.controller
        self.custom_init_data = custom_init_data

        self.quota_cache = QuotaManagement()
        self.policy = None

        quota_checker = None

        # check if the policy is being overridden:
        if 'quotaChecker' in self.custom_init_data:
            quota_checker = self.custom_init_data.get('quotaChecker')
            if 'disable' in quota_checker and quota_checker['disable']:
                logging.info("QuotaManager is disabled in configuration.")
                return

        else:
            quota_checker = controller.get('quotaChecker')
            if not quota_checker or not quota_checker.get('enabled'):
                logger.info("QuotaManager is disabled in configuration.")
                return

        self.quota_checker_policy_rule = quota_checker.get('quotaCheckerPolicyRule')
        if not self.quota_checker_policy_rule:
            logger.warning(
                "No quota checker policy rule found. Quota management will not be enforced.")
            return

        try:
            self.policy = self.load_quota_checker_policy_rule()
        except ValueError as e:
            logger.error(f"Failed to load policy: {e}")
            return

        logger.info("QuotaManager successfully initialized.")

    def load_quota_checker_policy_rule(self):
        if not self.quota_checker_policy_rule:
            raise ValueError("Missing quotaCheckerPolicyRule configuration.")

        policy_rule_uri = self.quota_checker_policy_rule.get(
            'policyRuleURI', '')
        parameters = self.quota_checker_policy_rule.get('parameters', {})

        if not policy_rule_uri:
            raise ValueError(
                "Missing policyRuleURI in quotaCheckerPolicyRule.")

        logger.info(f"Loading quota checker policy from {policy_rule_uri}")

        return LocalPolicyEvaluator(policy_rule_uri=policy_rule_uri, parameters=parameters)

    def check_quota(self, session_id: str, input_data) -> bool:
        if not self.policy:
            return True

        try:
            new_quota = self.quota_cache.increment(session_id)
            logger.debug(
                f"Session {session_id} quota incremented to {new_quota}")

            policy_input = {
                "quota_table": self.quota_cache,
                "input": input_data,
                "quota": new_quota,
                "session_id": session_id
            }
            result = self.policy.execute_policy_rule(policy_input)

            logger.info(f"[Quota checker output]: {result}")

            allowed = result.get("allowed", False)

            logger.info(
                f"Quota check for session {session_id}: {'Allowed' if allowed else 'Denied'}")
            return allowed
        except ValueError as ve:
            logger.error(
                f"Invalid quota increment attempt: {ve}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error in check_quota: {e}", exc_info=True)
            return False


class QuotaManagerAPIServer:
    def __init__(self, quota_store, quota_policy: QuotaManager, app):
        self.quota_store = quota_store
        self.quota_policy = quota_policy

        # Register REST API routes
        app.add_url_rule("/quota/<session_id>", "get_quota",
                         self.get_quota, methods=["GET"])
        app.add_url_rule("/quota/reset/<session_id>",
                         "reset_quota", self.reset_quota, methods=["POST"])
        app.add_url_rule("/quota/exists/<session_id>",
                         "quota_exists", self.quota_exists, methods=["GET"])
        app.add_url_rule("/quota/<session_id>", "remove_quota",
                         self.remove_quota, methods=["DELETE"])
        app.add_url_rule("/quota/mgmt", "mgmt_quota",
                         self.mgmt_quota_checker, methods=["POST"])

    def mgmt_quota_checker(self):
        try:

            data = request.json

            mgmt_action = data["mgmt_action"]
            mgmt_data = data["mgmt_data"]

            response = self.quota_policy.policy.execute_mgmt_command(mgmt_action, mgmt_data)
            return jsonify({"success": True, "data": response}), 200
            
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    def get_quota(self, session_id):
        try:
            quota = self.quota_store.get(session_id)
            return jsonify({"session_id": session_id, "quota": quota}), 200
        except Exception as e:
            logger.error(f"Error getting quota for {session_id}: {e}")
            return jsonify({"error": "Failed to fetch quota"}), 500

    def reset_quota(self, session_id):
        try:
            self.quota_store.reset(session_id)
            return jsonify({"message": f"Quota reset for session {session_id}"}), 200
        except Exception as e:
            logger.error(f"Error resetting quota for {session_id}: {e}")
            return jsonify({"error": "Failed to reset quota"}), 500

    def quota_exists(self, session_id):
        try:
            exists = self.quota_store.exists(session_id)
            return jsonify({"session_id": session_id, "exists": exists}), 200
        except Exception as e:
            logger.error(
                f"Error checking quota existence for {session_id}: {e}")
            return jsonify({"error": "Failed to check quota existence"}), 500

    def remove_quota(self, session_id):
        try:
            self.quota_store.remove(session_id)
            return jsonify({"message": f"Quota removed for session {session_id}"}), 200
        except Exception as e:
            logger.error(f"Error removing quota for {session_id}: {e}")
            return jsonify({"error": "Failed to remove quota"}), 500
