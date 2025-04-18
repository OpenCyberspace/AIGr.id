import requests
import os
import json

from .policy_sandbox import LocalPolicyEvaluator
from .global_metrics import GlobalClusterMetricsClient
from .node_mgmt import NodeManagementAPIs


class ClusterPoliciesExecutor:

    def __init__(self, policies_map={}) -> None:
        self.policies_map = policies_map

    def check_for_action(self, action, input_data):
        try:
            if action not in self.policies_map:
                return True, input_data

            policy_rule_uri = self.policies_map.get(action, None)
            policy_rule = LocalPolicyEvaluator(policy_rule_uri=policy_rule_uri)
            result = policy_rule.execute_policy_rule(input_data)

            return result['allowed'], result['input_data']

        except Exception as e:
            return False, str(e)

    def handle_node_addition(self, cluster_id, node_data):
        try:

            if 'add_node' in self.policies_map:

                cluster_db = ClusterClient()
                ret, cluster = cluster_db.read_cluster(cluster_id)
                if not ret:
                    raise Exception(f"cluster {cluster_id} not found")

                # obtain the cluster metrics from global DB:
                cluster_metrics_db = GlobalClusterMetricsClient()
                metrics = cluster_metrics_db.get_cluster(cluster_id)

                input_data = {
                    "node_data": node_data,
                    "cluster_data": cluster,
                    "cluster_metrics": metrics
                }

                allowed, modified_node_data = self.check_for_action(
                    "add_node", input_data)
                if not allowed:
                    raise Exception(modified_node_data)

                config = cluster["config"]

                if not 'urlMap' in config:
                    raise Exception("config did not provide URL MAP")

                urlMap = config['urlMap']
                controller_url = urlMap.get("controllerService")

                if not controller_url:
                    raise Exception("cluster did not provide a controller URL")

                node_mgmt = NodeManagementAPIs(controller_url)
                data = node_mgmt.add_node(modified_node_data)

                return data

            else:
                cluster_db = ClusterClient()
                ret, cluster = cluster_db.read_cluster(cluster_id)
                if not ret:
                    raise Exception(f"cluster {cluster_id} not found")

                config = cluster["config"]

                if not 'urlMap' in config:
                    raise Exception("config did not provide URL MAP")

                urlMap = config['urlMap']
                controller_url = urlMap.get("controllerService")

                if not controller_url:
                    raise Exception("cluster did not provide a controller URL")

                node_mgmt = NodeManagementAPIs(controller_url)
                data = node_mgmt.add_node(modified_node_data)

                return data

        except Exception as e:
            raise e

    def handle_node_removal(self, cluster_id: str, node_id: str):
        try:
            if 'remove_node' in self.policies_map:
                cluster_db = ClusterClient()
                ret, cluster = cluster_db.read_cluster(cluster_id)
                if not ret:
                    raise Exception(f"cluster {cluster_id} not found")

                # obtain the cluster metrics from global DB:
                cluster_metrics_db = GlobalClusterMetricsClient()
                metrics = cluster_metrics_db.get_cluster(cluster_id)

                input_data = {
                    "node_id": node_id,
                    "cluster_data": cluster,
                    "cluster_metrics": metrics
                }

                allowed, modified_node_data = self.check_for_action(
                    "remove_node", input_data)
                if not allowed:
                    raise Exception(modified_node_data)

                config = cluster["config"]

                if not 'urlMap' in config:
                    raise Exception("config did not provide URL MAP")

                urlMap = config['urlMap']
                controller_url = urlMap.get("controllerService")

                if not controller_url:
                    raise Exception("cluster did not provide a controller URL")

                node_mgmt = NodeManagementAPIs(controller_url)
                data = node_mgmt.remove_node(modified_node_data)

                return data
            else:
                cluster_db = ClusterClient()
                ret, cluster = cluster_db.read_cluster(cluster_id)
                if not ret:
                    raise Exception(f"cluster {cluster_id} not found")

                config = cluster["config"]

                if not 'urlMap' in config:
                    raise Exception("config did not provide URL MAP")

                urlMap = config['urlMap']
                controller_url = urlMap.get("controllerService")

                if not controller_url:
                    raise Exception("cluster did not provide a controller URL")

                node_mgmt = NodeManagementAPIs(controller_url)
                data = node_mgmt.remove_node(modified_node_data)

                return data

        except Exception as e:
            raise e

    def add_cluster_to_network(self, cluster_data: dict):
        try:
            if 'add_cluster' in self.policies_map:
                allowed, modified_cluster_data = self.check_for_action(
                    "add_cluster", cluster_data)
                if not allowed:
                    raise Exception(modified_cluster_data)
            else:
                modified_cluster_data = cluster_data

            return modified_cluster_data

        except Exception as e:
            raise e

    def remove_cluster_from_network(self, cluster_id: str, cluster_data: dict):
        try:
            if 'remove_cluster' in self.policies_map:
                allowed, modified_cluster_data = self.check_for_action(
                    "remove_cluster", cluster_data)
                if not allowed:
                    raise Exception(modified_cluster_data)
            else:
                modified_cluster_data = cluster_data

            return modified_cluster_data

        except Exception as e:
            raise e


class ClusterClient:
    def __init__(self):
        self.base_url = os.getenv(
            "CLUSTER_SERVICE_URL", "http://localhost:3000")

        actions_map = json.loads(
            os.getenv("CLUSTER_CONTROLLER_GATEWAY_ACTIONS_MAP", '{}'))
        self.actions_executor = ClusterPoliciesExecutor(actions_map)

    def add_node_to_cluster(self, cluster_id, node_data):
        try:

            response = self.actions_executor.handle_node_addition(
                cluster_id, node_data)
            return response

        except Exception as e:
            raise e

    def remove_node_from_cluster(self, cluster_id, node_id):
        try:

            response = self.actions_executor.handle_node_removal(
                cluster_id, node_id)
            return response

        except Exception as e:
            raise e

    def create_cluster(self, cluster_data):
        try:

            # evaluate the create cluster policy
            allowed, cluster_data = self.actions_executor.check_for_action("create_cluster", input_data=cluster_data)
            if not allowed:
                raise Exception(
                    f"cluster not allowed to be added: {cluster_data}")

            response = requests.post(
                f"{self.base_url}/clusters", json=cluster_data)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as http_err:
            return False, f"HTTP error occurred: {http_err}"
        except Exception as err:
            return False, f"Error occurred: {err}"

    def read_cluster(self, cluster_id):
        try:
            response = requests.get(f"{self.base_url}/clusters/{cluster_id}")
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as http_err:
            return False, f"HTTP error occurred: {http_err}"
        except Exception as err:
            return False, f"Error occurred: {err}"

    def update_cluster(self, cluster_id, update_data):
        try:
            response = requests.put(
                f"{self.base_url}/clusters/{cluster_id}", json=update_data)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as http_err:
            return False, f"HTTP error occurred: {http_err}"
        except Exception as err:
            return False, f"Error occurred: {err}"

    def delete_cluster(self, cluster_id):
        try:

            allowed, cluster_data = self.actions_executor.check_for_action(
                "remove_cluster", {"cluster_id": cluster_id})
            if not allowed:
                raise Exception(
                    f"cluster not allowed to be added: {cluster_data}")

            response = requests.delete(
                f"{self.base_url}/clusters/{cluster_id}")
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as http_err:
            return False, f"HTTP error occurred: {http_err}"
        except Exception as err:
            return False, f"Error occurred: {err}"

    def execute_query(self, query):
        try:
            response = requests.post(
                f"{self.base_url}/clusters/query", json={"query": query})
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as http_err:
            return False, f"HTTP error occurred: {http_err}"
        except Exception as err:
            return False, f"Error occurred: {err}"
