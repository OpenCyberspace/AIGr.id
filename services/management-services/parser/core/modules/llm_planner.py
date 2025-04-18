import requests
import logging
import os
import json
import datetime

from .static_policy import StaticPolicyDeployer

from ..webhooks.component_registry import ComponentRegistry
from ..webhooks.clusters import ClusterClient
from ..webhooks.blocks import BlocksClient
from ..webhooks.clusters import ClusterClient

from ..utils import generate_unique_alphanumeric_string, stream_download


class TaskClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def create_task(self, task_data):
        url = f"{self.base_url}/task"
        try:
            response = requests.post(url, json=task_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create task: {e}")
            return {"error": str(e)}

    def read_task(self, task_id):
        url = f"{self.base_url}/task/{task_id}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to read task with ID {task_id}: {e}")
            return {"error": str(e)}

    def update_task(self, task_id, update_data):
        url = f"{self.base_url}/task/{task_id}"
        try:
            response = requests.put(url, json=update_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to update task with ID {task_id}: {e}")
            return {"error": str(e)}

    def delete_task(self, task_id):
        url = f"{self.base_url}/task/{task_id}"
        try:
            response = requests.delete(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to delete task with ID {task_id}: {e}")
            return {"error": str(e)}

    def set_task_as_complete(self, task_id):
        url = f"{self.base_url}/task/{task_id}/complete"
        try:
            response = requests.put(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to set task as complete with ID {task_id}: {e}")
            return {"error": str(e)}


class LayerClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def get_layer(self, layer_hash):
        url = f"{self.base_url}/layer/{layer_hash}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to get layer with hash {layer_hash}: {e}")
            return {"error": str(e)}

    def create_layer(self, data):
        url = f"{self.base_url}/layer"
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create layer: {e}")
            return {"error": str(e)}

    def update_layer(self, layer_hash, data):
        url = f"{self.base_url}/layer/{layer_hash}"
        try:
            response = requests.put(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to update layer with hash {layer_hash}: {e}")
            return {"error": str(e)}

    def delete_layer(self, layer_hash):
        url = f"{self.base_url}/layer/{layer_hash}"
        try:
            response = requests.delete(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to delete layer with hash {layer_hash}: {e}")
            return {"error": str(e)}

    def add_block_id(self, layer_hash, block_id):
        url = f"{self.base_url}/layer/{layer_hash}/block_id"
        data = {"block_id": block_id}
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to add block ID {block_id} to layer with hash {layer_hash}: {e}")
            return {"error": str(e)}

    def remove_block_id(self, layer_hash, block_id):
        url = f"{self.base_url}/layer/{layer_hash}/block_id"
        data = {"block_id": block_id}
        try:
            response = requests.delete(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to remove block ID {block_id} from layer with hash {layer_hash}: {e}")
            return {"error": str(e)}

    def add_vdag_id(self, layer_hash, vdag_id):
        url = f"{self.base_url}/layer/{layer_hash}/vdag_id"
        data = {"vdag_id": vdag_id}
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to add vdag ID {vdag_id} to layer with hash {layer_hash}: {e}")
            return {"error": str(e)}

    def remove_vdag_id(self, layer_hash, vdag_id):
        url = f"{self.base_url}/layer/{layer_hash}/vdag_id"
        data = {"vdag_id": vdag_id}
        try:
            response = requests.delete(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to remove vdag ID {vdag_id} from layer with hash {layer_hash}: {e}")
            return {"error": str(e)}

    def query_by_component_id(self, component_id):
        url = f"{self.base_url}/layer/query/component_id"
        params = {"component_id": component_id}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to query by component ID {component_id}: {e}")
            return {"error": str(e)}

    def query_by_block_id_and_vdag_id(self, block_id, vdag_id):
        url = f"{self.base_url}/layer/query/block_id_and_vdag_id"
        params = {"block_id": block_id, "vdag_id": vdag_id}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Failed to query by block ID {block_id} and vdag ID {vdag_id}: {e}")
            return {"error": str(e)}

    def generic_query(self, query):
        url = f"{self.base_url}/layer/query"
        try:
            response = requests.post(url, json=query)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to perform generic query: {e}")
            return {"error": str(e)}


class LLMPlanner:

    def __init__(self, ir: dict) -> None:

        self.block_data = ir
        self.component_uri = self.block_data['componentUri']
        ret, component_data = ComponentRegistry.GetComponentByURI(
            self.component_uri)
        if not ret:
            raise Exception(str(component_data))
        self.component_data = component_data
        self.name = "planner-" + generate_unique_alphanumeric_string(5)

    def execute(self):
        try:

            # 1. deploy a static policy rule:
            planner_policy_rule = self.block_data['policies']['plannerPolicy']

            deployer = StaticPolicyDeployer(
                os.getenv("POLICY_RULE_REMOTE_URL"))
            resp = deployer.deploy_policy_rule_service(
                self.name, policy_rule_id=planner_policy_rule['policyRuleURI'],
                node="policies", initial_replicas=1
            )

            if 'success' in resp and not resp['success']:
                raise Exception(resp['message'])

            # 2. obtain component data:
            config = self.component_data['componentConfig']

            model_config = None

            if 'modelConfig' not in config:
                if 'modelFileURL' not in config:
                    raise Exception("model file not found")

                model_data_bytes = stream_download(config['modelFileURL'])
                model_config = model_data_bytes.decode("utf-8")
            else:
                model_config = config['modelConfig']

            # 3. execute initial plan api:
            resp = deployer.execute_rpc(self.name, {
                "mode": "plan",
                "modelConfig": model_config,
                "component": self.component_data,
                "parameters":  planner_policy_rule['parameters']
            })

            if 'success' in resp and not resp['success']:
                raise Exception(resp['message'])

            # pass this data to the coordinator:
            resp = resp['message']

            layout = resp['layout']

            return layout

        except Exception as e:
            raise e


def create_llm_vdag(task_data):

    task_client = TaskClient(base_url=os.getenv("LLM_PLANNER_TASK_API"))

    task_payload = {
        "task_id": task_data['task_id'],
        "status": "pending",
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "input_payload": task_data.get('input_payload', {}),
        "k8s_job_id": task_data.get('k8s_job_id', "")
    }
    task_response = task_client.create_task(task_payload)

    if "error" in task_response:
        raise Exception(f"Failed to create task: {task_response['error']}")

    planner = LLMPlanner(task_data)
    layout = planner.execute()

    return layout


class LLMVDAGCreator:
    def __init__(self):
        self.task_client = TaskClient(
            base_url=os.getenv("LLM_PLANNER_TASK_API"))
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def create_llm_vdag(self, ir):
        try:
            input_payload = ir.get('input_payload', {})
            component_uri = input_payload.get('component_uri')
            model_plan_data = input_payload.get('model_plan_data')

            task_payload = {
                "task_id": ir['taskId'],
                "status": "pending",
                "start_time": datetime.now(),
                "end_time": None,
                "input_payload": input_payload,
                "k8s_job_id": ir.get('k8sJobId', "")
            }
            
            self.task_client.create_task(task_payload)

            planner = LLMPlanner({
                "componentUri": component_uri,
                "policies": {
                    "plannerPolicy": {
                        "parameters": model_plan_data,
                        "policyRuleURI": input_payload.get('checkerPolicyRuleUri')
                    }
                }
            })
            layout = planner.execute()
            return layout

        except Exception as e:
            self.logger.error(f"Failed to create LLM VDAG: {e}")
            raise
