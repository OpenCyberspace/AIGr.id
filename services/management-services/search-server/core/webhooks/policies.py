import requests
import os


class PoliciesQueryClient:
    def __init__(self):
        self.base_url = os.getenv("POLICIES_SERVER_URL").rstrip("/")

    def query_functions(self, query_filter: dict):

        return self._post_request("/function/query", query_filter)

    def query_graphs(self, query_filter: dict):

        return self._post_request("/graphs/query", query_filter)

    def query_policies(self, query_filter: dict):

        return self._post_request("/policy/query", query_filter)

    def _post_request(self, endpoint: str, query_filter: dict):

        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, json=query_filter)

        try:
            response_data = response.json()
        except ValueError:
            raise Exception("Invalid JSON response from API.")

        if response.status_code == 200 and response_data.get("success"):
            return response_data.get("data", [])
        else:
            raise Exception(response_data.get(
                "message", "Unknown error occurred."))
