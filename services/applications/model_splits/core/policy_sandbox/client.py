import requests
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict

@dataclass
class PolicyRule:
    policy_rule_uri: str
    name: str
    version: str
    release_tag: str
    metadata: Dict
    tags: str
    code: str
    code_type: str
    type: str
    policy_input_schema: Dict
    policy_output_schema: Dict
    policy_settings_schema: Dict
    policy_parameters_schema: Dict
    policy_settings: Dict
    policy_parameters: Dict
    description: str
    functionality_data: Dict

    @staticmethod
    def from_dict(data: Dict) -> 'PolicyRule':
        return PolicyRule(
            policy_rule_uri=f"{data['name']}:{data['version']}-{data['release_tag']}",
            name=data['name'],
            version=data['version'],
            release_tag=data['release_tag'],
            metadata=data['metadata'],
            tags=data['tags'],
            code=data['code'],
            code_type=data['code_type'],
            type=data['type'],
            policy_input_schema=data['policy_input_schema'],
            policy_output_schema=data['policy_output_schema'],
            policy_settings_schema=data['policy_settings_schema'],
            policy_parameters_schema=data['policy_parameters_schema'],
            policy_settings=data['policy_settings'],
            policy_parameters=data['policy_parameters'],
            description=data['description'],
            functionality_data=data['functionality_data']
        )

    def to_dict(self) -> Dict:
        return asdict(self)


class PolicyDBClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def create_policy(self, policy: PolicyRule) -> bool:
        url = f"{self.base_url}/policy"
        try:
            response = requests.post(url, json=policy.to_dict())
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return True
                else:
                    print(f"Error: {data.get('message')}")
            else:
                print(f"Failed to create policy. Status Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        return False

    def read_policy(self, policy_rule_uri: str) -> Optional[PolicyRule]:
        url = f"{self.base_url}/policy/{policy_rule_uri}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return PolicyRule.from_dict(data["data"])
                else:
                    print(f"Error: {data.get('message')}")
            else:
                print(f"Failed to read policy. Status Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        return None

    def update_policy(self, policy_rule_uri: str, updated_policy: PolicyRule) -> bool:
        url = f"{self.base_url}/policy/{policy_rule_uri}"
        try:
            response = requests.put(url, json=updated_policy.to_dict())
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return True
                else:
                    print(f"Error: {data.get('message')}")
            else:
                print(f"Failed to update policy. Status Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        return False

    def delete_policy(self, policy_rule_uri: str) -> bool:
        url = f"{self.base_url}/policy/{policy_rule_uri}"
        try:
            response = requests.delete(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return True
                else:
                    print(f"Error: {data.get('message')}")
            else:
                print(f"Failed to delete policy. Status Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        return False

    def query_policies(self, query_filter: dict) -> List[PolicyRule]:
        url = f"{self.base_url}/policy/query"
        try:
            response = requests.post(url, json=query_filter)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return [PolicyRule.from_dict(policy) for policy in data["data"]]
                else:
                    print(f"Error: {data.get('message')}")
            else:
                print(f"Failed to query policies. Status Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        return []


