import requests
import os
import time
import threading
import logging

from flask import Flask, request, jsonify
from .schema import vDAGObject
from .policy_sandbox import LocalPolicyEvaluator

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BlocksDB:
    def __init__(self, base_url, max_retries):
        self.base_url = base_url
        self.cache = {}
        self.max_retries = max_retries

    def get_block_by_id(self, block_id):
        try:
            logger.info(f"Fetching block by ID: {block_id}")
            response = requests.get(f'{self.base_url}/blocks/{block_id}')
            if response.status_code != 200:
                error_msg = f"API returned non-200 status code: {response.status_code}, Response: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            logger.info(f"Successfully retrieved block: {block_id}")
            return True, response.json()
        except Exception as e:
            logger.error(f"Error fetching block {block_id}: {e}")
            return False, str(e)

    def get_block_url(self, block_id):
        try:
            logger.info(f"Retrieving block URL for ID: {block_id}")
            success, block = self.get_block_by_id(block_id)
            if not success:
                raise Exception(
                    f"No block found in the DB with ID {block_id}: {block}")

            cluster_data = block.get('cluster', {})
            config = cluster_data.get('config', {})
            public_gateway_url = config.get('public_gateway_url', '')

            if not public_gateway_url:
                raise Exception(
                    f"Missing 'public_gateway_url' for block {block_id}")

            url = f"{public_gateway_url}/{block_id}/mgmt"
            logger.info(f"Generated block URL: {url}")
            return url

        except Exception as e:
            logger.error(f"Error retrieving block URL: {e}")
            raise e

    def get_block_url_with_cache(self, block_id):
        try:
            if block_id in self.cache:
                logger.info(f"Using cached block URL for {block_id}")
                return self.cache[block_id]

            url = self.get_block_url(block_id)
            self.cache[block_id] = url
            return url

        except Exception as e:
            logger.error(f"Error fetching block URL from cache: {e}")
            raise e

    def check_health(self, block_ids):
        health_results = {}

        base_url = os.getenv("GLOBAL_BLOCK_METRICS_URL", "http://34.58.1.86:30201")

        for block_id in block_ids:
            try:
                url = f"{base_url}/block/health/{block_id}"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                data = response.json()

                if not data.get("success", False):
                    logger.warning(f"Health check failed for block {block_id}: success=False in response")
                    health_results[block_id] = {"healthy": False, "error": "Unsuccessful response"}
                    continue

                health_results[block_id] = {
                    "healthy": data.get("healthy", False),
                    "instances": data.get("instances", [])
                }

            except Exception as e:
                logger.error(f"Error checking health for block {block_id}: {e}")
                health_results[block_id] = {"healthy": False, "error": str(e)}

        return health_results


class HealthChecker:
    def __init__(self, vdag_info: vDAGObject, app: Flask, custom_init_data: dict) -> None:

        self.policy = None

        self.vdag_info = vdag_info
        controller = self.vdag_info.controller
        self.custom_init_data = custom_init_data

        logger.info(f"[custom init data] {self.custom_init_data}")

        self.is_initialized = False
        self.blocks_db = BlocksDB(os.getenv("BLOCKS_DB_URL"), max_retries=3)

        health_checker = None

        if 'healthChecker' in self.custom_init_data:
            health_checker = self.custom_init_data.get('healthChecker')
            if 'disable' in health_checker and health_checker['disable']:
                logging.info("HealthChecker is disabled in configuration.")
                return
        else:
            health_checker = controller.get('healthChecker', None)
            if not health_checker or not health_checker.get('enabled', False):
                logger.info("HealthChecker is disabled in configuration.")
                return
        

        self.health_checker_policy_rule = health_checker.get('healthCheckerPolicyRule', None)
        if not self.health_checker_policy_rule:
            logger.warning("No health checker policy rule found.")
            return

        self.interval = int(health_checker.get('interval', 60))
        self.max_retries = int(health_checker.get('maxRetries', 1))
        self.policy = self.load_health_checker_policy_rule()
        self.is_initialized = True
        logger.info("HealthChecker successfully initialized.")

        # register health check API:
        app.add_url_rule("/health/check", "health_check", self.run_health_check_adhoc, methods=["GET"])
        app.add_url_rule("/health/mgmt", "health_mgmt", self.mgmt, methods=["POST"])

    def load_health_checker_policy_rule(self):
        try:
            policy_rule_uri = self.health_checker_policy_rule.get(
                'policyRuleURI', '')
            parameters = self.health_checker_policy_rule.get('settings', {})

            if not policy_rule_uri:
                raise Exception("Missing policyRuleURI in healthCheckerPolicyRule")

            logger.info(
                f"Loading health checker policy from {policy_rule_uri}")
            return LocalPolicyEvaluator(policy_rule_uri=policy_rule_uri, parameters=parameters)

        except Exception as e:
            logger.error(f"Error loading health checker policy: {e}")
            raise e

    def check_health(self, block_ids, mode="default"):
        try:
            if not self.policy:
                raise Exception("Health check policy is not initialized")

            if mode == "default":

                health_results = self.blocks_db.check_health(block_ids)
                logger.info("Executing policy rule for health check results.")
                return self.policy.execute_policy_rule({
                    "mode": mode,
                    "vdag": self.vdag_info.to_dict(),
                    "health_check_data": health_results
                })
            else:
                logger.info("Executing policy rule for health check results in fast check mode.")
                return self.policy.execute_policy_rule({
                    "mode": mode,
                    "vdag": self.vdag_info.to_dict(),
                    "health_check_data": {}
                })

        except Exception as e:
            logger.error(f"Error in check_health: {e}")
            raise e

    def is_healthy_fast_check(self):
        try:

            if not self.policy:
                return True

            all_blocks = []
            for _, block in self.vdag_info.assignment_info.items():
                all_blocks.append(block)

            response = self.check_health(all_blocks, mode="fast_check")
            return response['overall_healthy']
        except Exception as e:
            logger.error("health checker failed, returning True")
            return True

    def run_health_check_adhoc(self):
        try:
            all_blocks = []
            for _, block in self.vdag_info.assignment_info.items():
                all_blocks.append(block)

            response =  self.check_health(all_blocks)
            return jsonify({"success": True, "data": response}), 200

        except Exception as e:
            return jsonify({"success": False, "data": response}), 500

    def mgmt(self):
        try:

            data = request.json
            mgmt_action = data.get('mgmt_action', "")
            mgmt_data = data.get('mgmt_data', {})

            response =  self.policy.execute_mgmt_command(mgmt_action, mgmt_data)
            return jsonify({"success": True, "data": response}), 200
            
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    def run_health_checker(self):
        while not self.stop_event.is_set():
            try:
                all_blocks = []

                for _, block in self.vdag_info.assignment_info.items():
                    all_blocks.append(block)

                if all_blocks:
                    logger.info(
                        f"Running periodic health check for {len(all_blocks)} blocks.")
                    self.check_health(all_blocks)
            except Exception as e:
                logger.error(f"Health check error: {e}")

            time.sleep(self.interval)

    def start_health_checker(self):
        if not self.is_initialized:
            logger.warning("Health checker is not initialized")
            return

        if hasattr(self, 'thread') and self.thread.is_alive():
            logger.warning("Health checker is already running.")
            return

        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self.run_health_checker, daemon=True)
        self.thread.start()
        logger.info("Health checker started.")

    def stop_health_checker(self):
        if hasattr(self, 'stop_event'):
            self.stop_event.set()
            if hasattr(self, 'thread'):
                self.thread.join()
            logger.info("Health checker stopped.")
        else:
            logger.warning("Health checker was not running.")
