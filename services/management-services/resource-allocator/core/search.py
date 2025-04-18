import requests
import json
import os


class SearchClient:
    def __init__(self):
        self.base_url = os.getenv("SEARCH_SERVER_API_URL", "http://localhost:12000")

    def filter_data(self, input_data):
        try:
            response = requests.post(
                f"{self.base_url}/api/filter-data", json=input_data)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("success"):
                return response_data["data"]
            else:
                raise Exception(response_data.get(
                    "message", "Unknown error occurred"))

        except Exception as e:
            raise Exception(f"Error in filter_data: {str(e)}")

    def similarity_search(self, input_data):
        try:
            response = requests.post(
                f"{self.base_url}/api/similarity-search", json=input_data)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("success"):
                return response_data["data"]
            else:
                raise Exception(response_data.get("message", "Unknown error occurred"))

        except Exception as e:
            raise Exception(f"Error in similarity_search: {str(e)}")

