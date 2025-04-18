import os
import requests


class vDAGProcessingAPI:
    def __init__(self):
        self.base_url = os.getenv(
            "VDAG_SYSTEM_URL", "http://localhost:10500").rstrip('/')

    def submit_task(self, task_data):
        url = f"{self.base_url}/submitTask"
        response = requests.post(url, json=task_data)
        return self._handle_response(response)

    def _handle_response(self, response):
        try:
            result = response.json()
        except requests.exceptions.JSONDecodeError:
            response.raise_for_status()
            raise Exception("Invalid JSON response from server")

        if response.status_code == 200 and result.get("success"):
            return result["data"]

        error_message = result.get("message", "Unknown error occurred")
        raise Exception(error_message)


class vDAGDryRunAPIs:
    def __init__(self):
        self.base_url = os.getenv(
            "VDAG_SYSTEM_URL", "http://localhost:10500").rstrip('/')

    def _post(self, endpoint, input_data):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(url, json=input_data)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("success"):
                return response_data["data"]
            else:
                raise Exception(response_data.get(
                    "message", "Unknown error occurred"))

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    def dryrun_assignment_policy(self, input_data):
        return self._post("/dryrun/assignment-policy", input_data)

    def dryrun_end_to_end(self, input_data):
        return self._post("/dryrun/end-to-end", input_data)

    def validate_graph(self, input_data):
        return self._post("/dryrun/validate-graph", input_data)
