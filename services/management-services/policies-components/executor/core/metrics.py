import requests
import os
class ClusterMetricsClient:
    def __init__(self, base_url, cluster_id="cluster-123"):
        self.base_url = base_url.rstrip('/')
        self.cluster_id = cluster_id

    def get_cluster_metrics(self):
        response = requests.get(f"{self.base_url}/cluster")
        if response.status_code == 200:
            return response.json()["data"]
        raise Exception(response.json().get("error", "Unknown error"))


def get_metrics(cluster_client):
    
    cluster_metrics = cluster_client.get_cluster_metrics()
    return cluster_metrics


def get_metrics_collector():

    base_uri = os.getenv("CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000")

    cluster_client = ClusterMetricsClient(base_uri)

    def collector():
        return get_metrics(cluster_client)
    return collector
