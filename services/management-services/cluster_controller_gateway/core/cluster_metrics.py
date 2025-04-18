import requests
import logging
import os

from .cluster_db import ClusterClient


logger = logging.getLogger(__name__)


class ClusterMetricsClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def _handle_response(self, response):
        try:
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            return False, str(http_err)
        except Exception as err:
            logger.error(f"Error occurred: {err}")
            return False, str(err)

    def get_node(self, node_id):
        try:
            url = f"{self.base_url}/node/{node_id}"
            response = self.session.get(url)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error in get_node request: {e}")
            return False, str(e)

    def query_node(self, query_params):
        try:
            url = f"{self.base_url}/node/query"
            response = self.session.get(url, params=query_params)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error in query_node request: {e}")
            return False, str(e)

    def get_cluster_metrics(self):
        try:
            url = f"{self.base_url}/cluster"
            response = self.session.get(url)
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error in get_cluster_metrics request: {e}")
            return False, str(e)


def get_cluster_metrics_connection(cluster_id):
    try:

        cluster_client = ClusterClient()
        ret, resp = cluster_client.read_cluster(cluster_id)

        if not ret:
            raise Exception(resp)

        config = resp["config"]

        if not 'urlMap' in config:
            raise Exception("config did not provide URL MAP")

        urlMap = config['urlMap']
        metricsUrl = urlMap.get("metricsService")

        return ClusterMetricsClient(base_url=metricsUrl)

    except Exception as e:
        raise e
