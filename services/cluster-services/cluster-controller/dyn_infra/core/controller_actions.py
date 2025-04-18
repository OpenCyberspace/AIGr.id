import requests
import json
import logging
import os

class ClusterControllerExecutor:

    def __init__(self, base_url):
        self.base_url = base_url
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
        payload['cluster_id'] = os.getenv("CLUSTER_ID")

        print('sending payload', payload)

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

    def failed_instances(self, payload):
        return self.execute_action("failed_pods", payload)



