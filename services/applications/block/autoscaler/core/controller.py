import requests
import json
import logging
import os


class ClusterControllerExecutor:

    def __init__(self):
        self.base_url = os.getenv("CONTROLLER_URL", "http://localhost:4000")
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def execute_action(self, action, payload):
        url = f"{self.base_url}/executeAction"
        payload['action'] = action
        payload['cluster_id'] = os.getenv("CLUSTER_ID", "cluster-123")

        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(
                url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            self.logger.info(f"Response: {response.json()}")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            self.logger.error(f"HTTP error occurred: {http_err}")
            return {"success": False, "data": f"HTTP error occurred: {http_err}"}
        except Exception as err:
            self.logger.error(f"Other error occurred: {err}")
            return {"success": False, "data": f"Other error occurred: {err}"}

    def remove_block(self, payload):
        return self.execute_action("remove_block", payload)

    def create_block(self, payload):
        return self.execute_action("create_block", payload)

    def parameter_update(self, payload):
        return self.execute_action("parameter_update", payload)

    def scale_instance(self, payload):
        return self.execute_action("scale", payload)

    def remove_instance(self, payload):
        return self.execute_action("remove_instance", payload)

    def resource_allocation(self, payload):
        return self.execute_action("resource_allocation", payload)
