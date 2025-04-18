import requests
import os


class vDAGMetricsQuery:
    def __init__(self):

        self.base_url = os.getenv("VDAG_METRICS_SERVER_URL")
        self.endpoint = f"{self.base_url}/vdag/query"

    def query(self, query_filter: dict):

        try:
            response = requests.post(self.endpoint, json=query_filter)
            response_json = response.json()

            if response.status_code == 200 and response_json.get("success"):
                return response_json["data"]
            else:
                error_msg = response_json.get(
                    "error", "Unknown error occurred")
                raise ValueError(f"vDAG query failed: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Request to vDAG API failed: {e}")
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Unexpected error in vDAGMetricsQuery: {e}")
