import requests
import os


class ClusterClient:
    def __init__(self):
        self.base_url = os.getenv("CLUSTER_SERVICE_URL", "http://localhost:3000")

    def create_cluster(self, cluster_data):
        try:
            response = requests.post(
                f"{self.base_url}/clusters", json=cluster_data)
            print(response.status_code, response.text)
            response.raise_for_status()
            return True, response.json()
        except Exception as err:
            return False, response.json()

    def read_cluster(self, cluster_id):
        try:
            response = requests.get(f"{self.base_url}/clusters/{cluster_id}")
            response.raise_for_status()
            return True, response.json()
        except Exception as err:
            return False, f"Error occurred: {err}"

    def update_cluster(self, cluster_id, update_data):
        try:
            response = requests.put(
                f"{self.base_url}/clusters/{cluster_id}", json=update_data)
            response.raise_for_status()
            return True, response.json()
        except Exception as err:
            return False, f"Error occurred: {err}"

    def delete_cluster(self, cluster_id):
        try:
            response = requests.delete(
                f"{self.base_url}/clusters/{cluster_id}")
            response.raise_for_status()
            return True, response.json()
        except Exception as err:
            return False, f"Error occurred: {err}"

    def execute_query(self, query):
        try:
            response = requests.post(
                f"{self.base_url}/clusters/query", json={"query": query})
            response.raise_for_status()
            return True, response.json()
        except Exception as err:
            return False, f"Error occurred: {err}"
