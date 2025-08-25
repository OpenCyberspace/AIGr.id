import requests
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class APIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class GlobalClusterMetricsClient:
    def __init__(self):
        self.base_url = os.getenv(
            "GLOBAL_CLUSTER_METRICS_URL", "http://localhost:8888").rstrip('/')
        logger.info(
            f"GlobalClusterMetricsClient initialized with base URL: {self.base_url}")

    def _handle_response(self, response):
        try:
            response.raise_for_status()
            json_data = response.json()
            if not json_data.get("success", False):
                raise APIError(json_data.get(
                    "error", "Unknown error"), response.status_code)
            return json_data.get("data")
        except requests.RequestException as e:
            logger.error(f"HTTP error: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise

    def create_cluster(self, cluster_data):
        url = f"{self.base_url}/cluster"
        response = requests.post(url, json=cluster_data)
        return self._handle_response(response)

    def update_cluster(self, cluster_id, update_data):
        url = f"{self.base_url}/cluster/{cluster_id}"
        response = requests.put(url, json=update_data)
        return self._handle_response(response)

    def delete_cluster(self, cluster_id):
        url = f"{self.base_url}/cluster/{cluster_id}"
        response = requests.delete(url)
        return self._handle_response(response)

    def get_cluster(self, cluster_id):
        url = f"{self.base_url}/cluster/{cluster_id}"
        response = requests.get(url)
        return self._handle_response(response)

    def query_clusters(self, query_params=None):
        url = f"{self.base_url}/cluster/query"
        response = requests.post(url, json=query_params)
        return self._handle_response(response)


class GlobalBlocksMetricsClient:
    def __init__(self):
        self.base_url = os.getenv("GLOBAL_BLOCK_METRICS_URL", "http://localhost:8889").rstrip('/')
        logger.info(
            f"GlobalBlocksMetricsClient initialized with base URL: {self.base_url}")

    def _handle_response(self, response):
        try:
            response.raise_for_status()
            json_data = response.json()
            if not json_data.get("success", False):
                raise APIError(json_data.get(
                    "error", "Unknown error"), response.status_code)
            return json_data.get("data")
        except requests.RequestException as e:
            logger.error(f"HTTP error: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise

    def create_block(self, block_data):
        url = f"{self.base_url}/block"
        response = requests.post(url, json=block_data)
        return self._handle_response(response)

    def update_block(self, block_id, update_data):
        url = f"{self.base_url}/block/{block_id}"
        response = requests.put(url, json=update_data)
        return self._handle_response(response)

    def delete_block(self, block_id):
        url = f"{self.base_url}/block/{block_id}"
        response = requests.delete(url)
        return self._handle_response(response)

    def get_block(self, block_id):
        url = f"{self.base_url}/block/{block_id}"
        response = requests.get(url)
        return self._handle_response(response)

    def query_blocks(self, query_params=None):
        url = f"{self.base_url}/block/query"
        response = requests.post(url, json=query_params)
        return self._handle_response(response)
    
    def aggregate_blocks(self, pipeline):
        url = f"{self.base_url}/block/aggregate"
        try:
            response = requests.post(url, json=pipeline)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error calling aggregate_blocks: {e}")
            raise