import requests
import os


class SpecAPIClient:
    def __init__(self):
        self.base_url = os.getenv("SPEC_STORE_API_URL", "")

    def get_spec(self, spec_uri):
        url = f"{self.base_url}/spec/{spec_uri}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data.get("data")
        else:
            error_data = response.json()
            raise Exception(error_data.get("error", "Unknown error"))


class TemplateAPIClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def execute_template_policy(self, template_uri, input_data=None, parameters=None):
        url = f"{self.base_url}/template/execute"
        payload = {
            "template_uri": template_uri,
            "input_data": input_data or {},
            "parameters": parameters or {}
        }
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            return data.get("data")
        else:
            error_data = response.json()
            raise Exception(error_data.get("error", "Unknown error"))
