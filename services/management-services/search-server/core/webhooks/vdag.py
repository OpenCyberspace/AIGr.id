import requests
import os

class vDAGsClient:
    def __init__(self):
        self.base_url = os.getenv("VDAG_SERVICE_URL")

    def get_vdag(self, vdagURI):
        url = f"{self.base_url}/vdag/{vdagURI}"
        response = requests.get(url)
        return self._handle_response(response)

    def query_vdags(self, query_filter):
        url = f"{self.base_url}/vdags"
        response = requests.post(url, json=query_filter)
        return self._handle_response(response)

    def _handle_response(self, response):
        try:
            result = response.json()
        except requests.exceptions.JSONDecodeError:
            response.raise_for_status()
            raise Exception("Invalid JSON response from server")
        
        if response.status_code == 200 and result.get("success"):
            return result["data"]
        
        error_message = result.get("error", "Unknown error occurred")
        raise Exception(error_message)