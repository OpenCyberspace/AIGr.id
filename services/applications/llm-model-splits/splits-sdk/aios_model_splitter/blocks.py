import os
from typing import Dict, Any, Union, List
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlocksClient:

    def __init__(self):
        self.BASE_URL = os.getenv(
            "BLOCKS_DB_URL", "http://localhost:3001")

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

    
    def query_blocks(self, query: Dict[str, Any]) -> Union[List[Dict[str, Any]], str]:
        try:
            response = requests.post(
                f'{self.BASE_URL}/blocks/query', json=query, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}



class Blocks:

    def __init__(self) -> None:
        self.blocks_query = BlocksClient()
    
    def query(self, component_uri: str, hash: str):
        try:

            q = {
                "componentUri":  component_uri,
                "blockInitData.layerHash": hash
            }

            return self.blocks_query.query_blocks(q)
            
        except Exception as e:
            raise e