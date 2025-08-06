import requests
import os


class BlockMetricsClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def insert_document(self, document):
        response = requests.post(
            f"{self.base_url}/block/insert", json=document)
        if response.status_code == 200:
            return response.json()["data"]
        raise Exception(response.json().get("data", "Unknown error"))

    def update_document(self, node_id, update_fields):
        payload = {"nodeId": node_id, "updateFields": update_fields}
        response = requests.put(f"{self.base_url}/block/update", json=payload)
        if response.status_code == 200:
            return response.json()["data"]
        raise Exception(response.json().get("data", "Unknown error"))

    def delete_document(self, node_id):
        payload = {"nodeId": node_id}
        response = requests.delete(
            f"{self.base_url}/block/delete", json=payload)
        if response.status_code == 200:
            return response.json()["data"]
        raise Exception(response.json().get("data", "Unknown error"))

    def get_by_block_id(self, block_id):
        response = requests.get(f"{self.base_url}/block/{block_id}")
        if response.status_code == 200:
            return response.json()["data"]
        raise Exception(response.json().get("data", "Unknown error"))

    def query_documents(self, query_filter):
        response = requests.post(
            f"{self.base_url}/block/query", json=query_filter)
        if response.status_code == 200:
            return response.json()["data"]
        raise Exception(response.json().get("data", "Unknown error"))


class ClusterMetricsClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def get_cluster_metrics(self):
        response = requests.get(f"{self.base_url}/cluster")
        if response.status_code == 200:
            return response.json()["data"]
        raise Exception(response.json().get("error", "Unknown error"))

def get_block_metrics(block_id: str):

    base_uri = os.getenv("CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000")
    block_metrics = BlockMetricsClient(base_uri)
    return block_metrics.get_by_block_id(block_id)

def get_block_metrics_collector():
    return get_block_metrics



def get_metrics(block_client, cluster_client, block_id):
    block_metrics = block_client.get_by_block_id(block_id)
    cluster_metrics = cluster_client.get_cluster_metrics()
    return {
        "block_metrics": block_metrics,
        "cluster_metrics": cluster_metrics
    }


def get_metrics_collector(block_id):

    base_uri = os.getenv("CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000")

    cluster_client = ClusterMetricsClient(base_uri)
    block_client = BlockMetricsClient(base_uri)

    def collector():
        return get_metrics(block_client, cluster_client, block_id)
    return collector

def get_cluster_metrics_collector():
    base_uri = os.getenv("CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000")

    cluster_client = ClusterMetricsClient(base_uri)

    def collector():
        return cluster_client.get_cluster_metrics()
    
    return collector