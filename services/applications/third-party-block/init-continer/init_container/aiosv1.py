import requests
import os
import json

import logging


def get_envs():
    controller_url = os.getenv("CONTROLLER_URL", "localhost:5000")
    block_id = os.getenv("BLOCK_ID", "default-block")
    operating_mode = os.getenv("OPERATING_MODE", "create")
    cluster_id = os.getenv("CLUSTER_ID")

    return {
        "controller_url": controller_url,
        "block_id": block_id,
        "operating_mode": operating_mode,
        "cluster_id": cluster_id
    }


class ClusterControllerExecutor:

    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)ss'
        )

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def execute_action(self, action, payload):
        url = f"{self.base_url}/executeAction"
        payload['action'] = action
        payload['cluster_id'] = os.getenv("CLUSTER_ID")

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


class ClusterController:

    def __init__(self) -> None:
        self.envs = get_envs()
        self.block_id = self.envs['block_id']
        self.cluster_connector = ClusterControllerExecutor(
            self.envs["controller_url"]
        )

    def send_status_update(self, payload):
        try:
            action = ""
            if self.envs["operating_mode"] == "create":
                action = "init_create_status_update"
            else:
                action = "init_remove_status_update"

            payload["block_id"] = self.block_id

            resp = self.cluster_connector.execute_action(
                action, payload
            )

            if 'success' in resp and not resp['success']:
                raise Exception(resp['data'])

            return resp

        except Exception as e:
            raise e
