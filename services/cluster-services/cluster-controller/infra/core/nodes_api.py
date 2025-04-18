import os
import requests

class NodesAPIClient:
    def __init__(self):
        self.base_url = os.getenv("NODES_CLIENT_API_URL", "http://localhost:8500")

    def get_healthy_nodes(self):
        url = f"{self.base_url}/healthy_nodes"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data["nodes"]
            else:
                raise Exception(data.get("message", "Unknown error from server"))
        except Exception as e:
            raise Exception(f"Failed to fetch healthy nodes: {e}")

    def get_nodes_status(self):
        url = f"{self.base_url}/nodes_status"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data["nodes_status"]
            else:
                raise Exception(data.get("message", "Unknown error from server"))
        except Exception as e:
            raise Exception(f"Failed to fetch nodes status: {e}")


