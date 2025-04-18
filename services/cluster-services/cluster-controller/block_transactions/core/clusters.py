import requests
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClustersClient:
    def __init__(self):
        self.base_url = os.getenv("CLUSTER_SERVICE_URL")

    def create_cluster(self, data):
        try:
            response = requests.post(f'{self.base_url}/clusters', json=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Cluster created: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating cluster: {e}")
            return None

    def read_cluster(self, cluster_id):
        response = None
        try:
            response = requests.get(f'{self.base_url}/clusters/{cluster_id}')
            response.raise_for_status()
            result = response.json()
            logger.info(f"Cluster read: {result}")
            return result
        except requests.exceptions.RequestException as e:
            if response and response.status_code == 404:
                logger.warning(f"Cluster not found: {cluster_id}")
            else:
                logger.error(f"Error reading cluster: {e}")
            return None

    def update_cluster(self, cluster_id, data):
        response = None
        try:
            response = requests.put(
                f'{self.base_url}/clusters/{cluster_id}', json=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Cluster updated: {result}")
            return result
        except requests.exceptions.RequestException as e:
            if response and response.status_code == 404:
                logger.warning(f"Cluster not found: {cluster_id}")
            else:
                logger.error(f"Error updating cluster: {e}")
            return None

    def delete_cluster(self, cluster_id):
        response = None
        try:
            response = requests.delete(
                f'{self.base_url}/clusters/{cluster_id}')
            response.raise_for_status()
            result = response.json()
            logger.info(f"Cluster deleted: {result}")
            return result
        except requests.exceptions.RequestException as e:
            if response and response.status_code == 404:
                logger.warning(f"Cluster not found: {cluster_id}")
            else:
                logger.error(f"Error deleting cluster: {e}")
            return None

    def execute_query(self, query):
        try:
            response = requests.post(
                f'{self.base_url}/clusters/query', json={'query': query})
            response.raise_for_status()
            result = response.json()
            logger.info(f"Query executed: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error executing query: {e}")
            return None

class CurrentClusterClient(ClustersClient):
    def __init__(self):
        super().__init__()

    def read_cluster_from_env(self):
        cluster_id = os.getenv('CLUSTER_ID')
        if not cluster_id:
            logger.error("Environment variable 'CLUSTER_ID' not set")
            return None
        return self.read_cluster(cluster_id)

    def query(self, base_query):
        cluster_id = os.getenv('CLUSTER_ID')
        if not cluster_id:
            logger.error("Environment variable 'CLUSTER_ID' not set")
            return None

        query_with_filter = {
            "$and": [
                base_query,
                {"id": cluster_id}
            ]
        }
        return self.execute_query(query_with_filter)
    
    def add_node(self, new_node):
        cluster_id = os.getenv('CLUSTER_ID')
        if not cluster_id:
            logger.error("Environment variable 'CLUSTER_ID' not set")
            return None

        update_data = {
            "$push": {"nodes.nodeData": new_node},
            "$inc": {"nodes.count": 1}
        }

        return self.update_cluster(cluster_id, update_data)

    def update_config(self, new_config):
        cluster_id = os.getenv('CLUSTER_ID')
        if not cluster_id:
            logger.error("Environment variable 'CLUSTER_ID' not set")
            return None

        update_data = {
            "$set": {"config": new_config}
        }

        return self.update_cluster(cluster_id, update_data)
