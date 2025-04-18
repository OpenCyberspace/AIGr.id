import os
from typing import Dict, Any, Union, List
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlocksClient:

    def __init__(self):
        self.BASE_URL = os.getenv("BLOCKS_SERVICE_URL")

    def _handle_response(self, response: requests.Response) -> Union[Dict[str, Any], List[Dict[str, Any]], str]:
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            return {'error': f'HTTP error occurred: {http_err}'}
        except Exception as err:
            return {'error': f'Other error occurred: {err}'}

        try:
            return response.json()
        except ValueError:
            return response.text

    def create_block(self, block_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        try:
            response = requests.post(
                f'{self.BASE_URL}/blocks', json=block_data, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def get_all_blocks(self) -> Union[List[Dict[str, Any]], str]:
        try:
            response = requests.get(f'{self.BASE_URL}/blocks', timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def get_block_by_id(self, block_id: str) -> Union[Dict[str, Any], str]:
        try:
            response = requests.get(
                f'{self.BASE_URL}/blocks/{block_id}', timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def update_block_by_id(self, block_id: str, block_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        try:
            response = requests.put(
                f'{self.BASE_URL}/blocks/{block_id}', json=block_data, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def delete_block_by_id(self, block_id: str) -> Union[Dict[str, Any], str]:
        try:
            response = requests.delete(
                f'{self.BASE_URL}/blocks/{block_id}', timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def query_blocks(self, query: Dict[str, Any]) -> Union[List[Dict[str, Any]], str]:
        try:
            response = requests.post(
                f'{self.BASE_URL}/blocks/query', json=query, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}


class ClusteredBlockClient(BlocksClient):
    def __init__(self):
        super().__init__()
        self.cluster_id = os.getenv('CLUSTER_ID')
        if not self.cluster_id:
            raise ValueError('CLUSTER_ID environment variable is not set')

    def get_block_by_id(self, block_id: str) -> Union[Dict[str, Any], str]:
        try:
            response = super().get_block_by_id(block_id)
            if isinstance(response, dict) and 'cluster' in response:
                if response['cluster']['clusterId'] == self.cluster_id:
                    return response
                else:
                    return {'error': 'Block does not belong to the specified cluster'}
            return response
        except Exception as e:
            logger.error(f'Error getting block by ID: {block_id}. Error: {e}')
            return {'error': str(e)}

    def get_all_blocks_in_cluster(self) -> Union[List[Dict[str, Any]], str]:
        try:
            query = {'cluster.clusterId': self.cluster_id}
            return self.query_blocks(query)
        except Exception as e:
            logger.error(
                f'Error getting all blocks in cluster: {self.cluster_id}. Error: {e}')
            return {'error': str(e)}

    def query_blocks_in_cluster(self, query: Dict[str, Any]) -> Union[List[Dict[str, Any]], str]:
        try:
            if not query:
                query = {}
            query['cluster.clusterId'] = self.cluster_id
            return self.query_blocks(query)
        except Exception as e:
            logger.error(
                f'Error querying blocks in cluster: {self.cluster_id} with query: {query}. Error: {e}')
            return {'error': str(e)}
