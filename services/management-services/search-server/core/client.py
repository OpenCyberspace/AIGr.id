import os
import logging
import requests
from typing import Dict, Any, Optional


class SearchServerAPI:

    def __init__(self):
        self.base_url = os.getenv("SEARCH_SERVER_API_URL")
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
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for {endpoint}: {str(e)}")
            return {"success": False, "message": str(e)}
