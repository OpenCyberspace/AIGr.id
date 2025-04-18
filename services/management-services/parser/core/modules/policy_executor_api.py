import requests
import logging


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
