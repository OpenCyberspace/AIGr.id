import requests
import logging
import os
from typing import Dict, Any

from .schema import vDAGObject

logger = logging.getLogger(__name__)


class vDAGDBClient:
    def __init__(self):
        self.base_url = os.getenv(
            "VDAG_DB_SERVICE_URL", "http://localhost:10501")

    def create_vdag(self, vdag: vDAGObject):
        try:
            response = requests.post(
                f"{self.base_url}/vdag", json=vdag.to_dict())
            response.raise_for_status()
            return True, response.json()["data"]
        except requests.RequestException as e:
            logger.error(f"Error creating vDAG: {e}")
            return False, str(e)

    def get_vdag(self, vdagURI: str):
        try:
            response = requests.get(f"{self.base_url}/vdag/{vdagURI}")
            response.raise_for_status()
            data = response.json()["data"]
            return True, vDAGObject.from_dict(data)
        except requests.RequestException as e:
            logger.error(f"Error retrieving vDAG: {e}")
            return False, str(e)

    def update_vdag(self, vdagURI: str, update_fields: dict):
        try:
            response = requests.put(
                f"{self.base_url}/vdag/{vdagURI}", json=update_fields)
            response.raise_for_status()
            return True, response.json()["data"]
        except requests.RequestException as e:
            logger.error(f"Error updating vDAG: {e}")
            return False, str(e)

    def delete_vdag(self, vdagURI: str):
        try:
            response = requests.delete(f"{self.base_url}/vdag/{vdagURI}")
            response.raise_for_status()
            return True, response.json()["data"]
        except requests.RequestException as e:
            logger.error(f"Error deleting vDAG: {e}")
            return False, str(e)

    def query_vdags(self, query_filter: dict):
        try:
            response = requests.post(
                f"{self.base_url}/vdags", json=query_filter)
            response.raise_for_status()
            data = response.json()["data"]
            vdags = [vDAGObject.from_dict(doc) for doc in data]
            return True, vdags
        except requests.RequestException as e:
            logger.error(f"Error querying vDAGs: {e}")
            return False, str(e)


class SearchServerAPI:

    def __init__(self):
        self.base_url = os.getenv(
            "SEARCH_SERVER_API_URL", "http://localhost:12000")
        if not self.base_url:
            raise ValueError(
                "SEARCH_SERVER_API_URL environment variable is not set")

    def similarity_search(self, policy_rule_uri: str, parameters: dict) -> Dict[str, Any]:

        payload = {
            "rankingPolicyRule": {
                "policyRuleURI": policy_rule_uri,
                "parameters": parameters
            }
        }
        return self._post_request("/api/no-ir/similarity-search", payload)

    def filter_search(self, match_type: str, filter_query: str) -> Dict[str, Any]:

        payload = {"matchType": match_type, "filter": filter_query}
        return self._post_request("/api/no-ir/filter", payload)

    def _post_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:

        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["data"]
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for {endpoint}: {str(e)}")
            return {"success": False, "message": str(e)}
