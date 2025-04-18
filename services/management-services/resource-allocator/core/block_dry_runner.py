import requests
import logging
import os

from .policy_sandbox import LocalPolicyEvaluator
from .policy_sandbox.code_executor import LocalCodeExecutor
from .default_policies import DefaultClusterResourceAllocatorPolicy


class PolicyRemoteExecutor:
    def __init__(self, api_url, policy_rule_id, inputs, parameters):
        self.api_url = api_url
        self.policy_rule_id = policy_rule_id
        self.inputs = inputs
        self.parameters = parameters

    def execute(self):
        payload = {
            "policy_rule_id": self.policy_rule_id,
            "policy_rule_inputs": self.inputs,
            "policy_rule_parameters": self.parameters
        }
        try:
            logging.info(
                f"Sending request to {self.api_url}/evaluatePolicyRule with payload: {payload}")
            response = requests.post(
                f"{self.api_url}/evaluatePolicyRule", json=payload)
            response.raise_for_status()
            logging.info("Received response successfully.")
            return response.json()
        except requests.RequestException as e:
            logging.error(f"API request failed: {e}")
            return {"success": False, "message": str(e)}


class DryRunExecutor:
    def __init__(self, mode: str = "", block_policy_uri: str = "", settings: dict = {}, parameters: dict = {}, remote_url: str = None) -> None:

        print('here!')
        self.mode = mode
        self.block_policy_uri = block_policy_uri
        self.settings = settings
        self.parameters = parameters
        self.remote_url = remote_url or os.getenv("POLICY_RULE_REMOTE_URL")

        if self.mode != "remote":
            self.local_evaluator = self._load_if_local(block_policy_uri)
        else:
            self.remote_evaluator = self._initialize_remote_executor()

    def _load_if_local(self, uri: str):
        return LocalPolicyEvaluator(uri, self.settings, self.parameters, custom_class=DefaultClusterResourceAllocatorPolicy)

    def _initialize_remote_executor(self):
        if not self.remote_url:
            raise ValueError(
                "Remote URL must be provided for remote execution.")
        return PolicyRemoteExecutor(self.remote_url, self.block_policy_uri, None, None)

    def execute(self, payload: dict, selection_mode: str):
        try:
            payload['action'] = selection_mode

            if self.mode != "remote":
                logging.info(f"Executing locally with mode: {selection_mode}")
                return self.local_evaluator.execute_policy_rule(payload)
            else:
                logging.info(f"Executing remotely with mode: {selection_mode}")
                self.remote_evaluator.inputs = payload
                self.remote_evaluator.parameters = payload
                response = self.remote_evaluator.execute()
                if response.get("success"):
                    return response.get("policy_rule_output", {})
                raise Exception(response.get(
                    "message", "Unknown error from remote execution"))
        except Exception as e:
            logging.error(f"Execution failed for mode {selection_mode}: {e}")
            raise

    def execute_dry_run(self, payload: dict):
        return self.execute(payload, "dry_run")

    def execute_resource_alloc(self, payload: dict):
        return self.execute(payload, "allocation")

    def execute_for_scale(self, payload: dict):
        return self.execute(payload, "scale")


class DryRunCodeExecutor:
    def __init__(self, block_data: dict, policy_data: dict) -> None:
        logging.info("Initializing DryRunCodeExecutor")
        self.block_data = block_data
        self.ranking_policy_rule = policy_data['rankingPolicyRule']
        self.settings = policy_data.get('settings', {})
        self.parameters = policy_data.get('parameters', {})

        self.policy_rule = LocalCodeExecutor(
            self.ranking_policy_rule['policyCodePath'], self.settings, self.parameters)
        self.filter = self.parameters.get('filterRule', {})

    def execute(self, inputs):
        try:
            ret, result = self.policy_rule.execute(inputs)
            if not ret:
                raise ValueError(f"Policy execution failed: {result}")
            return result
        except Exception as e:
            logging.error(f"Execution failed in DryRunCodeExecutor: {e}")
            raise
