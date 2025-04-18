import requests
import logging

class FailurePolicyClient:
    def __init__(self, api_url):
        self.api_url = api_url


    def execute_failure_policy(self, failure_policy_id, inputs, parameters):
        payload = {
            "failure_policy_id": failure_policy_id,
            "inputs": inputs,
            "parameters": parameters
        }
        try:
            logging.info(f"Sending request to {self.api_url}/executeFailurePolicy with payload: {payload}")
            response = requests.post(f"{self.api_url}/executeFailurePolicy", json=payload)
            if response.status_code == 200:
                data = response.json()['data']
                return data
            else:
                raise Exception(response['message'])
            
        except requests.RequestException as e:
            logging.error(f"API request failed: {e}")
            return {"success": False, "message": str(e)}
