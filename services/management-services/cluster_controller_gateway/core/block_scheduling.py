import os
import threading
import requests
import logging
from .policy_sandbox import LocalPolicyEvaluator
from .policy_sandbox.code_executor import LocalCodeExecutor
from .cluster_db import ClusterClient
from .cluster_controller import get_cluster_controller_connection_from_doc, get_cluster_controller_connection
from .default_policies import ClusterSelectorPolicyRule
from .filter_logic import SearchServerAPI
from .allocator_service import do_online_allocation
from .global_tasks_db import GlobalTasksDB

logging.basicConfig(level=logging.INFO)


class PayloadPusher:
    def __init__(self, hosts):
        self.hosts = hosts
        self.route = "/executeAction"
        self.results = []
        self.lock = threading.Lock()

    def _post_payload(self, host, payload):
        url = f"{host}{self.route}"
        try:

            logging.info("executing cluster request for URL: {}".format(url))

            response = requests.post(url, json=payload, timeout=None)

            logging.info("cluster controller response for {}: {}".format(url, response.text))

            response.raise_for_status()
            with self.lock:

                response_json = response.json()
                if response_json['success']:
                    self.results.append(response_json['data'])

                self.results.append(response.json())
            logging.info(f"Payload successfully posted to {url}")
        except requests.RequestException as e:
            logging.error(f"Error posting to {host}: {e}")
            raise e

    def call(self, payload):
        payload['action'] = "dry_run"
        threads = []
        for host in self.hosts:
            thread = threading.Thread(
                target=self._post_payload, args=(host, payload))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        return self.results


class PolicyRemoteExecutor:
    def __init__(self, api_url, policy_rule_id, inputs, parameters):
        self.api_url = api_url
        self.policy_rule_id = policy_rule_id
        self.inputs = inputs
        self.parameters = parameters

    def execute(self):
        payload = {
            "policy_rule_id": self.policy_rule_id,
            "policy_rule_inputs": self.inputs,
            "policy_rule_parameters": self.parameters,
        }
        try:
            logging.info(
                f"Sending payload to {self.api_url}/evaluatePolicyRule: {payload}")
            response = requests.post(
                f"{self.api_url}/evaluatePolicyRule", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Remote execution failed: {e}")
            return {"success": False, "message": str(e)}


class DryRunExecutor:
    def __init__(self, mode="", block_policy_uri="", settings=None, parameters=None):
        self.mode = mode
        self.block_policy_uri = block_policy_uri
        self.settings = settings or {}
        self.parameters = parameters or {}

        if self.mode == "code":
            self.local_evaluator = LocalCodeExecutor(
                block_policy_uri, self.settings, self.parameters)
        elif self.mode == "remote":
            self.remote_evaluator = PolicyRemoteExecutor(
                os.getenv("POLICY_RULE_REMOTE_URL"), block_policy_uri, None, None
            )
        else:
            self.local_evaluator = LocalPolicyEvaluator(
                block_policy_uri, self.settings, self.parameters
            )

    def execute(self, parameters, block_data):
        try:
            filter_type = "cluster"
            filter_logic = self.parameters.get("filter", {})
            search = SearchServerAPI()

            logging.info("filter inputs: {}".format(filter_logic))

            filter_result = search.filter_search(filter_type, filter_logic)

            if not filter_result:
                filter_result = []

            logging.info("filter result: {}".format(filter_logic))

            input_data = {"filter_result": filter_result,
                          "block_data": block_data}
            input_data['action'] = "selection"

            if self.mode == "code":
                return self.local_evaluator.execute(input_data)
            elif self.mode == "remote":
                self.remote_evaluator.inputs = input_data
                self.remote_evaluator.parameters = parameters
                response = self.remote_evaluator.execute()
                if response.get("success"):
                    return response.get("policy_rule_output")
                else:
                    logging.error(f"Remote execution error: {response}")
                    return {"error": response.get("message", "Unknown error")}
            else:
                return self.local_evaluator.execute_policy_rule(input_data)
        except Exception as e:
            logging.error(f"Execution error: {e}")
            raise

    def execute_post_selection(self, parameters, input_data):
        try:

            input_data['action'] = "post_dry_run"

            if self.mode == "code":
                return self.local_evaluator.execute(input_data)
            elif self.mode == "remote":
                self.remote_evaluator.inputs = input_data
                self.remote_evaluator.parameters = parameters
                response = self.remote_evaluator.execute()
                if response.get("success"):
                    return response.get("policy_rule_output")
                else:
                    logging.error(f"Remote execution error: {response}")
                    return {"error": response.get("message", "Unknown error")}
            else:
                return self.local_evaluator.execute_policy_rule(input_data)
        except Exception as e:
            logging.error(f"Execution error: {e}")
            raise


class ClusterSelector:
    def __init__(self, input_data):
        self.input_data = input_data
        self.cluster_db = ClusterClient()

        self.ranking_policy_rule = input_data.get("rankingPolicyRule", "")
        self.settings = input_data.get("settings", {})
        self.parameters = input_data.get("parameters", {})
        self.policy_code_path = input_data.get("policyCodePath", "")
        mode = input_data.get("executionMode", "local")
        if self.policy_code_path:
            mode = "code"

        self.selector_policy = DryRunExecutor(
            mode, self.ranking_policy_rule, self.settings, self.parameters)

    def select_clusters(self, block_data):
        logging.info(f"Selecting clusters using policy: {self.input_data}")
        return self.selector_policy.execute(self.parameters, block_data)


class PostDryRunEvaluator:
    def __init__(self, input_data):
        self.input_data = input_data
        self.cluster_db = ClusterClient()

        logging.info("post dry run input data: {}".format(input_data))

        self.ranking_policy_rule = input_data.get("rankingPolicyRule", "")
        self.settings = input_data.get("settings", {})
        self.parameters = input_data.get("parameters", {})
        self.policy_code_path = input_data.get("policyCodePath", "")
        mode = input_data.get("executionMode", "local")
        if self.policy_code_path:
            mode = "code"

        self.selector_policy = DryRunExecutor(
            mode, self.ranking_policy_rule, self.settings, self.parameters)

    def select_cluster(self, input_data):
        input_data['action'] = "post_dry_run"
        logging.info(f"Post-dry-run selection started: {input_data}")
        return self.selector_policy.execute_post_selection(self.parameters, input_data)


class OnlineAllocator:

    def __init__(self, input_data, mode="dry_run") -> None:
        self.input_data = input_data
        self.mode = mode

    def _select_post_dry_run(self, input_data):
        post_evaluator = PostDryRunEvaluator(input_data)
        return post_evaluator.select_cluster(input_data)

    def execute(self):
        try:

            return do_online_allocation({
                "input": self.input_data,
                "mode": self.mode
            })

        except Exception as e:
            raise e


class BlockCreator:
    def __init__(self, input_data, mode):
        self.input_data = input_data
        self.mode = mode

        self.execution_mode = os.getenv("ALLOCATION_EXECUTION_MODE", "online")

        if self.execution_mode == "online":
            self.ws_executor = OnlineAllocator(self.input_data, "dry_run")

    def _prepare_cluster_input(self):
        block_allocator_policy = self.input_data.get(
            "policies", {}).get("resourceAllocator", {})
        payload = {
            "block_data": self.input_data,
            "policy_rule_uri": block_allocator_policy.get("policyRuleURI", "default"),
            "inputs": self.input_data,
            "parameters": block_allocator_policy.get("parameters", {}),
            "settings": block_allocator_policy.get("settings", {}),
        }
        return payload

    def execute(self):

        if self.execution_mode == "online":
            selected_cluster_data = self.ws_executor.execute()

            if self.mode == "allocate":
                controller = get_cluster_controller_connection(
                    selected_cluster_data['id'])

                response = controller.resource_allocation({
                    "block_data": self.input_data
                })

                if not response['success']:
                    raise Exception(response['message'])

                return response['data']
            else:
                return selected_cluster_data

        if self.mode == "select_clusters":
            return self._select_clusters()
        elif self.mode == "dry_run":
            selected_clusters = self._select_clusters()
            clusters = selected_clusters.get("clusters", [])
            if not clusters:
                raise ValueError(
                    "No clusters matched for the given policy rule")

            print('selected clusters', clusters)

            hosts = [get_cluster_controller_connection_from_doc(
                cluster) for cluster in clusters]


            push_payload = self._prepare_cluster_input()
            payload_pusher = PayloadPusher(hosts)
            responses = payload_pusher.call(push_payload)
            print(responses)

            selection_payload = {
                "clusters": [
                    {
                        "id": cluster["id"],
                        "cluster": cluster,
                        "score_data": response.get("selection_score_data", {}),
                        "block_data": self.input_data,
                    }
                    for response, cluster in zip(responses, clusters)
                ]
            }

            return self._select_post_dry_run(selection_payload)

        elif self.mode == "allocate":

            block_creator = BlockCreator(self.input_data, "dry_run")
            selected_cluster_data = block_creator.execute()

            controller = get_cluster_controller_connection(
                selected_cluster_data['id'])

            response = controller.resource_allocation({
                "block_data": self.input_data
            })

            if not response['success']:
                raise Exception(response['message'])

            return response['data']

        else:
            raise ValueError(f"Unsupported mode: {self.mode}")

    def _select_clusters(self):
        cluster_allocator_policy = self.input_data.get(
            "policies", {}).get("clusterAllocator", {})
        if not cluster_allocator_policy:
            raise ValueError(
                "No 'clusterAllocator' policy found in block data")

        input_data = {
            "rankingPolicyRule": cluster_allocator_policy.get("policyRuleURI", ""),
            "settings": cluster_allocator_policy.get("settings", {}),
            "parameters": cluster_allocator_policy.get("parameters", {}),
            "policyCodePath": cluster_allocator_policy.get("codePath", ""),
            "executionMode": cluster_allocator_policy.get("executionMode", ""),
        }

        cluster_selector = ClusterSelector(input_data)
        return cluster_selector.select_clusters(self.input_data)

    def _select_post_dry_run(self, input_data):

        cluster_allocator_policy = self.input_data.get(
            "policies", {}).get("clusterAllocator", {})
        if not cluster_allocator_policy:
            raise ValueError(
                "No 'clusterAllocator' policy found in block data")

        ix = {
            "rankingPolicyRule": cluster_allocator_policy.get("policyRuleURI", ""),
            "settings": cluster_allocator_policy.get("settings", {}),
            "parameters": cluster_allocator_policy.get("parameters", {}),
            "policyCodePath": cluster_allocator_policy.get("codePath", ""),
            "executionMode": cluster_allocator_policy.get("executionMode", ""),
        }

        post_evaluator = PostDryRunEvaluator(ix)
        return post_evaluator.select_cluster(input_data)


class BlocksTaskHandler:

    def __init__(self, data: dict) -> None:
        self.data = data

    def create_task(self, task_type: str):
        try:
            tasks_client = GlobalTasksDB()
            task_id = tasks_client.create_task(
                task_type=task_type, task_data=self.data, task_status="pending")
            return task_id
        except Exception as e:
            raise e

    def update_task(self, task_id, status, task_status_data):
        try:
            tasks_client = GlobalTasksDB()
            tasks_client.update_task(task_id, status, task_status_data)
        except Exception as e:
            raise e

    def execute_dry_run(self):
        task_id = self.create_task("block_dry_run")

        def run():
            try:
                block_creator = BlockCreator(self.data, mode="dry_run")
                result = block_creator.execute()
                self.update_task(task_id, "completed", {"result": result})
            except Exception as e:
                self.update_task(task_id, "failed", {"error": str(e)})
        threading.Thread(target=run, daemon=True).start()
        return task_id

    def execute_allocation(self):
        task_id = self.create_task("block_allocation")

        def run():
            try:
                block_creator = BlockCreator(self.data, mode="allocate")
                result = block_creator.execute()
                self.update_task(task_id, "completed", {"result": result})
            except Exception as e:
                self.update_task(task_id, "failed", {"error": str(e)})
        threading.Thread(target=run, daemon=True).start()
        return task_id
