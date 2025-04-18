import requests
import os


class ClusterInfraManagement:
    def __init__(self):
        self.base_url = os.getenv(
            "CLUSTER_CONTROLLER_GATEWAY_URL", "http://localhost:4000")

    def add_node_to_cluster(self, cluster_id, node_data):
        url = f"{self.base_url}/nodes/add-node-to-cluster/{cluster_id}"
        response = requests.post(url, json=node_data)
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            return data["data"]
        else:
            raise Exception(
                data.get("message", "Failed to add node to cluster"))

    def create_cluster(self, cluster_data):
        url = f"{self.base_url}/clusters/create"
        response = requests.post(url, json=cluster_data)
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            return data["data"]
        else:
            raise Exception(data.get("data", "Failed to create cluster"))
