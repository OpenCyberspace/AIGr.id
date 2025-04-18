import requests
import json


class StaticPolicyDeployer:
    def __init__(self, base_url):
        
        self.base_url = base_url

    def deploy_policy_rule_service(self, name, policy_rule_id, node, initial_replicas):
        
        try:
            url = f"{self.base_url}/deployPolicyRuleService"
            headers = {'Content-Type': 'application/json'}

            # Prepare the payload with the provided arguments
            policy_parameters = {
                "name": name,
                "policy_rule_id": policy_rule_id,
                "node": node,
                "initial_replicas": initial_replicas
            }

            response = requests.post(url, headers=headers,
                                     data=json.dumps(policy_parameters))

            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"Failed with status code {response.status_code}"}
        except Exception as e:
            raise e


    def execute_rpc(self, name, input):
       
        try:
            url = f"{self.base_url}/executePolicyRule"
            headers = {'Content-Type': 'application/json'}

            # Prepare the payload with the provided arguments
            policy_parameters = {
                "policy_name": name,
                "input": input,
            }

            response = requests.post(url, headers=headers,
                                     data=json.dumps(policy_parameters))

            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"Failed with status code {response.status_code}"}
        except Exception as e:
            raise e

    def delete_policy_rule_service(self, policy_name):
       
        try:
            url = f"{self.base_url}/deletePolicyRuleService"
            headers = {'Content-Type': 'application/json'}
            data = {'policy_name': policy_name}
            response = requests.post(
                url, headers=headers, data=json.dumps(data))

            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"Failed with status code {response.status_code}"}
        except Exception as e:
            raise e
