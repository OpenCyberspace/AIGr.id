import os
from .client import PolicyDBClient
from .code_executor import LocalCodeExecutor
import logging
import os
import logging
import requests

import os

import logging
import os
import requests
import json

# Configure logging
logging.basicConfig(level=logging.INFO)


def execute_policy_request(policy_rule_uri, input_data, parameters=None):
    executor_id = os.getenv("POLICY_SYSTEM_EXECUTOR_ID", "executor-0")
    executor_host_url = os.getenv(
        "POLICY_EXECUTOR_HOST_URL", "http://localhost:10000")

    if not executor_id:
        logging.error(
            f"Executor URI for executor_id {executor_id} not found in environment variables.")
        raise Exception(
            f"Executor URI for executor_id {executor_id} not found in environment variables.")

    if not executor_host_url:
        logging.error(
            f"Executor URI for executor_id {executor_id} not found in environment variables.")
        return {"success": False, "message": "Executor URI not found"}

    url = f"{executor_host_url}/executor/{executor_id}/execute_policy"

    payload = {
        "policy_rule_uri": policy_rule_uri,
        "input_data": input_data,
        "parameters": parameters
    }

    try:
        logging.info(
            f"Sending request to {url} with payload: {json.dumps(payload, indent=2)}")

        response = requests.post(url, json=payload)

        logging.info(
            f"Received response from {url}: {response.status_code} - {response.text}")

        response.raise_for_status()

        response_data = response.json()
        return response_data['data']

    except Exception as e:
        logging.error(f"Error while sending request: {e}")
        raise e


class PolicyFunctionExecutor:
    def __init__(self, policy_rule_uri: str = None, parameters: dict = None, settings: dict = None, custom_class=None):

        self.executor = None
        self.custom_function = None
        self.mode = os.getenv("POLICY_EXECUTION_MODE", "local")

        if self.mode != "local":
            self.policy_rule_uri = policy_rule_uri
            self.parameters = parameters
            return

        if custom_class is not None:
            logging.info("Initializing directly from custom class")
            try:
                settings = settings or {}
                parameters = parameters or {}
                self.custom_function = custom_class("", settings, parameters)
                logging.info("Custom class initialized successfully")
            except Exception as e:
                logging.error(
                    f"Failed to initialize custom class '{custom_class.__name__}': {e}")
                raise
        else:
            self.policy_db = PolicyDBClient(os.getenv("POLICY_DB_URL", "http://localhost:10000"))

            logging.info(f"Fetching policy data for URI: {policy_rule_uri}")
            policy_data = self.policy_db.read_policy(policy_rule_uri)
            if not policy_data:
                raise ValueError(
                    f"Policy rule with URI '{policy_rule_uri}' not found.")

            logging.info("Determining parameters and settings for execution")
            policy_parameters = policy_data.policy_parameters
            if parameters is None:
                parameters = policy_parameters
            else:
                parameters.update(policy_parameters)

            if settings is None:
                settings = policy_data.policy_settings
            else:
                settings.update(policy_data.policy_settings)

            logging.info(
                f"Initializing LocalCodeExecutor for policy {policy_rule_uri}")
            try:
                self.executor = LocalCodeExecutor(
                    download_url=policy_data.code,
                    settings=settings,
                    parameters=parameters,
                )
                self.executor.init()
                logging.info("LocalCodeExecutor initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize LocalCodeExecutor: {e}")
                raise

    def execute_policy_rule(self, input_data: dict):

        if self.mode != "local":
            op = execute_policy_request(
                self.policy_rule_uri, input_data, self.parameters)
            return op

        if self.custom_function is not None:
            logging.info("Executing custom class directly")
            try:
                result = self.custom_function.eval({}, input_data, None)
                return result
            except Exception as e:
                logging.error(
                    f"Failed to execute custom class '{type(self.custom_function).__name__}': {e}")
                raise
        elif self.executor is not None:
            try:
                logging.info(
                    "Executing policy function through LocalCodeExecutor")
                result = self.executor.execute(input_data)
                return result
            except Exception as e:
                logging.error(
                    f"Failed to execute policy function for URI '{self.policy_rule_uri}': {e}")
                raise
        else:
            raise RuntimeError("No executor or custom class is initialized")
