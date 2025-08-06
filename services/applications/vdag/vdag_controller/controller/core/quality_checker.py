from .schema import vDAGObject
from .policy_sandbox import LocalPolicyEvaluator

import logging
import copy
from flask import jsonify, request
import threading

from queue import Queue


class QualityChecker:
    def __init__(self, vdag_info: vDAGObject, custom_init_data) -> None:
        self.vdag_info = vdag_info
        controller = self.vdag_info.controller

        self.policy = None
        self.queue = Queue()
        self.counter = 0

        self.custom_init_data = custom_init_data

        self.is_initialized = False

        quality_checker = None

        if 'qualityChecker' in self.custom_init_data:
            quality_checker = custom_init_data.get('qualityChecker')
            if 'disable' in quality_checker and quality_checker['disable']:
                logging.info("QualityChecker is disabled in configuration.")
                return

        else:
            quality_checker = controller.get('qualityChecker')
            if not quality_checker or not quality_checker.get('enabled'):
                logging.info("QualityChecker is disabled in configuration.")
                return

        self.interval = int(quality_checker.get('framesInterval', 100))

        logging.info(f"Quality checker interval: {self.interval}")

        self.quality_checker_policy_rule = quality_checker.get('qualityCheckerPolicyRule')
        if not self.quality_checker_policy_rule:
            logging.warning(
                "No quality checker policy rule found. Quality management will not be enforced.")
            return

        try:
            self.policy = self.load_quality_checker_policy_rule()
        except ValueError as e:
            logging.error(f"Failed to load policy: {e}")
            return

        logging.info("QualityChecker successfully initialized.")

        # Start background thread to process the queue
        if self.is_initialized:
            self.worker_thread = threading.Thread(
                target=self.process_quality_checks, daemon=True)
            self.worker_thread.start()

    def load_quality_checker_policy_rule(self):
        if not self.quality_checker_policy_rule:
            raise ValueError("Missing qualityCheckerPolicyRule configuration.")

        policy_rule_uri = self.quality_checker_policy_rule.get(
            'policyRuleURI', '')
        parameters = self.quality_checker_policy_rule.get('parameters', {})

        if not policy_rule_uri:
            raise ValueError(
                "Missing policyRuleURI in qualityCheckerPolicyRule.")

        logging.info(f"Loading quality checker policy from {policy_rule_uri}")

        policy = LocalPolicyEvaluator(
            policy_rule_uri=policy_rule_uri, parameters=parameters)
        self.is_initialized = True
        return policy

    def submit_for_quality_check(self, input_data) -> None:

        if not self.is_initialized:
            return

        self.counter += 1
        if self.counter % self.interval == 0:
            data_copy = copy.deepcopy(input_data)
            self.queue.put(data_copy)
            logging.info(f"Frame submitted for quality check: {data_copy}")

    def process_quality_checks(self):
        while True:
            input_data = self.queue.get()
            try:
                if self.policy:
                    self.policy.execute_policy_rule(
                        {"vdag_info": self.vdag_info, "input_data": input_data}
                    )
                    logging.info(f"Quality check executed for: {input_data}")
            except Exception as e:
                logging.error(
                    f"Error executing quality check: {e}", exc_info=True)


class QualityCheckerManagementServer:
    def __init__(self, qa: QualityChecker, app):
        self.quality_checker = qa

        app.add_url_rule("/quality/mgmt", "mgmt_quality", self.mgmt_quality_checker, methods=["POST"])
    
    def mgmt_quality_checker(self):
        try:

            data = request.json

            mgmt_action = data["mgmt_action"]
            mgmt_data = data["mgmt_data"]

            response = self.quality_checker.policy.execute_mgmt_command(mgmt_action, mgmt_data)
            return jsonify({"success": True, "data": response})
            
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
        