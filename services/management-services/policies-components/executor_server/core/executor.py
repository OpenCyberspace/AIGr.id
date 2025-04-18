import os
from .client import PolicyDBClient
from .code_executor import LocalCodeExecutor
import logging
import os
import logging

import os


class PolicyFunctionExecutor:
    def __init__(self, policy_rule_uri: str, parameters: dict):
        self.policy_db = PolicyDBClient(os.getenv("POLICY_DB_URL"))

        logging.info(f"Fetching policy data for URI: {policy_rule_uri}")
        policy_data = self.policy_db.read(policy_rule_uri)
        if not policy_data:
            raise ValueError(
                f"Policy rule with URI '{policy_rule_uri}' not found.")

        logging.info("Determining parameters for execution")
        policy_parameters = policy_data.policy_parameters
        if parameters is None:
            parameters = policy_parameters

        logging.info(
            f"Initializing LocalCodeExecutor for policy {policy_rule_uri}")
        try:
            self.executor = LocalCodeExecutor(
                download_url=policy_data.code,
                settings=policy_data.policy_settings,
                parameters=parameters,
            )
        except Exception as e:
            raise e

    def execute(self, input_data: dict):

        try:

            result = self.executor.execute(input_data)
            return result

        except Exception as e:
            logging.error(
                f"Failed to execute policy function for URI '{self.policy_rule_uri}': {e}")
            raise
