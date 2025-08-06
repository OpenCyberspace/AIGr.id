import requests
import os

class ParameterUpdater:
    def __init__(self):
        self.base_url = os.getenv("CLUSTER_CONTROLLER_GATEWAY_URL", "http://localhost:5000")

    def update_parameters(self, cluster_id: str, block_id: str, service: str, mgmt_command: str, mgmt_data: dict, instance_id: str):
        url = f"{self.base_url}/blocks/mgmt"
        payload = {
            "block_id": block_id,
            "service": service,
            "action": mgmt_command,
            "payload": mgmt_data,
            "cluster_id": cluster_id,
            "instance_id": instance_id
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
