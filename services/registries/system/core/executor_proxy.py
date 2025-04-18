import requests
from .db import PolicyDB, FunctionsDB
from .schema import PolicyRule, Graph, Function
from .graph import GraphsDB, is_dag


class ExecutorProxyClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def _handle_response(self, response):
        try:
            response_data = response.json()
        except ValueError:
            response.raise_for_status()
            raise Exception("Invalid JSON response from server")

        if response_data.get("success"):
            return response_data.get("data", response_data.get("message"))
        else:
            raise Exception(response_data.get(
                "message", "Unknown error occurred"))

    def execute_policy(self, policy_rule_uri, input_data, parameters=None):
        url = f"{self.base_url}/execute_policy"
        payload = {
            "policy_rule_uri": policy_rule_uri,
            "input_data": input_data,
            "parameters": parameters
        }
        response = requests.post(url, json=payload)
        return self._handle_response(response)

    def create_deployment(self, name, policy_rule_uri, policy_rule_parameters=None, replicas=1, autoscaling=None, node_selector=""):
        url = f"{self.base_url}/deployments"
        payload = {
            "name": name,
            "policy_rule_uri": policy_rule_uri,
            "policy_rule_parameters": policy_rule_parameters,
            "replicas": replicas,
            "autoscaling": autoscaling,
            "node_selector": node_selector
        }
        response = requests.post(url, json=payload)
        return self._handle_response(response)

    def remove_deployment(self, name):
        url = f"{self.base_url}/deployments/{name}"
        response = requests.delete(url)
        return self._handle_response(response)

    def call_function(self, name, input_data):
        url = f"{self.base_url}/call_function/{name}"
        response = requests.post(url, json=input_data)
        return self._handle_response(response)

    def create_job_with_estimate(self, name, policy_rule_uri, job_id, policy_rule_parameters=None, inputs=None):
        url = f"{self.base_url}/create_job_with_estimate"
        payload = {
            "name": name,
            "policy_rule_uri": policy_rule_uri,
            "job_id": job_id,
            "policy_rule_parameters": policy_rule_parameters,
            "inputs": inputs or {}
        }
        response = requests.post(url, json=payload)
        return self._handle_response(response)

    def estimate_deployment(self, mode, policy):
        url = f"{self.base_url}/estimator/estimate"
        payload = {"mode": mode, "policy": policy} if mode == "adhoc" else {
            "mode": mode, "policy_rule_uri": policy}
        response = requests.post(url, json=payload)
        return self._handle_response(response)

    def create_deployment_with_estimate(self, name, policy_rule_uri, policy_rule_parameters=None, replicas=1, autoscaling=None):
        url = f"{self.base_url}/deployments/deploy-with-estimate"
        payload = {
            "name": name,
            "policy_rule_uri": policy_rule_uri,
            "policy_rule_parameters": policy_rule_parameters,
            "replicas": replicas,
            "autoscaling": autoscaling
        }
        response = requests.post(url, json=payload)
        return self._handle_response(response)

    def estimate_graph(self, policies):
        try:
            failed_estimates = []
            passed_estimates = {}

            for policy in policies:
                try:
                    result = self.estimate_deployment(
                        mode="adhoc", policy=policy)
                    if 'allowed' in result:
                        passed_estimates[policy['policy_rule_uri']
                                         ] = result['node_id']
                    else:
                        failed_estimates.append(policy['policy_rule_uri'])
                except Exception as e:
                    failed_estimates.append(policy['policy_rule_uri'])

                return {
                    "passed_estimates": passed_estimates,
                    "failed_estimates": failed_estimates
                }
        except Exception as e:
            raise

    def deploy_adhoc_graph(self, policy_db: PolicyDB, graph_db: GraphsDB,  data):
        try:

            graph = data['graph']

            graph_obj = Graph.from_dict(graph)
            if not is_dag(graph_obj.graph_connection_data):
                raise Exception("graph is not valid")

            # 1. estimate:
            response = self.estimate_graph(data['policies'])
            if len(response['failed_estimates']) > 0:
                raise Exception(response['failed_estimates'])

            policies = data['policies']
            for policy in policies:
                policy_obj = PolicyRule.from_dict(policy)
                policy_db.create(policy_obj)

            allowed_deployments = response['passed_estimates']

            deploy_parameters = data['deploy_parameters']
            for policy in policies:
                deploy_param = deploy_parameters[policy['policy_rule_uri']]
                self.create_deployment(deploy_param['name'], policy['policy_rule_uri'], replicas=1, autoscaling=False, node_selector={
                    "nodeID": allowed_deployments[policy['policy_rule_uri']]
                })

            graph_db.create(graph_obj)

            return True

        except Exception as e:
            raise e

    def remove_adhoc_graph(self, policy_db: PolicyDB, graph_db: GraphsDB, functions_db: FunctionsDB, graph_uri: str):
        try:
            # remove the graph:
            graph_data = graph_db.read(graph_uri)
            graph_db.delete(graph_data.graph_uri)

            # remove deployments
            functions = graph_data.graph_function_ids
            for function_id in functions:

                function = functions_db.read(function_id)

                self.remove_deployment(function_id)

                policy = function.function_policy_rule_uri
                functions_db.delete(function_id)
                policy_db.delete(policy)

            return True

        except Exception as e:
            raise e
