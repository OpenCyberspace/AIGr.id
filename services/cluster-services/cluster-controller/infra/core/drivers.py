import random
import string
import requests
import os
from .blocks import BlocksClient
from .cluster_db import ClusterClient
from .k8s import (
    create_executor,
    remove_executor,
    create_single_instance,
    remove_single_instance,
    get_all_matching_instances,
    remove_deployments_with_blockID
)
from .dry_runner import DryRunExecutor
from .metrics import BlockMetricsClient, ClusterMetricsClient
from .single_instance_block import InitContainerManager
from .nodes_api import NodesAPIClient

import time
import logging
import copy
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_unique_alphanumeric_string(N):
    alphanumeric_characters = string.ascii_letters + string.digits
    return ''.join(random.choices(alphanumeric_characters, k=N)).lower()


def prepare_policy_rule_input_for_alloc(block_data):
    try:

        metrics_collector = ClusterMetricsClient(
            os.getenv("CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000"))
        cluster_metrics = metrics_collector.get_cluster_metrics()

        if 'cluster' not in block_data:
            ret, resp = ClusterClient().read_cluster(os.getenv("CLUSTER_ID"))
            if not ret:
                raise Exception("cluster data not found")
            block_data['cluster'] = resp

        cluster_data = block_data['cluster']

        # get all healthy nodes:
        healthy_nodes = NodesAPIClient().get_healthy_nodes()

        return {
            "block": block_data,
            "cluster": cluster_data,
            "cluster_metrics": cluster_metrics,
            "healthy_nodes": healthy_nodes
        }

    except Exception as e:
        raise e


def prepare_policy_rule_input_for_scale(block_id, block_data):
    try:

        cluster_url = os.getenv(
            "CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000")

        cluster_metrics_collector = ClusterMetricsClient(cluster_url)
        cluster_metrics = cluster_metrics_collector.get_cluster_metrics()

        cluster_data = block_data['cluster']

        # get block metrics:
        block_metrics_collector = BlockMetricsClient(cluster_url)
        block_metrics = block_metrics_collector.get_by_block_id(block_id)

        healthy_nodes = NodesAPIClient().get_healthy_nodes()

        return {
            "block": block_data,
            "cluster": cluster_data,
            "cluster_metrics": cluster_metrics,
            "block_metrics": block_metrics,
            "mode": "scale",
            "healthy_nodes": healthy_nodes
        }

    except Exception as e:
        raise e


def register_health_checker(block_id, block_data):
    try:
        policies = block_data.get('policies', {})
        if 'stabilityChecker' not in policies:
            logger.info(
                f'stabilityChecker is not enabled for the block {block_id}, skipping registration')
            return

    except Exception as e:
        logger.error(
            f"Error registering health checker for block {block_id}: {e}")
        raise


def create_block(message):
    try:
        block_data = message.get('block_data', {})
        db = BlocksClient()

        cluster_id = os.getenv("CLUSTER_ID", "cluster-123")

        # get cluster client and populate cluster data:
        cluster_client = ClusterClient()
        ret, resp = cluster_client.read_cluster(cluster_id)
        if not ret:
            raise Exception(f"cluster {cluster_id} not found")

        block_data['cluster'] = resp

        block_id = block_data['id']
        # block_data['id'] = block_id

        db.create_block(block_data)
        time.sleep(5)

        # check if it's a init container:
        if InitContainerManager.check_is_init_container(block_data):
            # create init block:
            ret, resp = InitContainerManager.create_init_container(block_data)
            if not ret:
                raise Exception(str(resp))
        else:
            node_port = create_executor(block_id, namespace="blocks")

            # update node port to DB:
            updated_block = BlocksClient().update_block_by_id(block_id, {
                "$set": {
                    "blockInitData.external_port": node_port
                }
            })

            create_instance(updated_block)

            time.sleep(5)
            register_health_checker(block_id, updated_block)

    except Exception as e:
        logger.error(f"Error creating block: {e}")
        raise


def get_node_id_and_gpus(block_data, mode="allocate"):
    try:

        block_allocator_policy = block_data.get(
            "policies", {}).get("resourceAllocator", None
                                )

        if not block_allocator_policy:
            raise Exception("block doesn't have a resource allocation policy")

        payload = {
            "block_data": block_data,
            "policy_rule_uri": block_allocator_policy.get("policyRuleURI", "default"),
            "inputs": block_data,
            "parameters": block_allocator_policy.get("parameters", {}),
            "settings": block_allocator_policy.get("settings", {}),
        }

        # call dry runner:
        dry_runner = DryRunExecutor(
            os.getenv("CLUSTER_DRY_RUN_MODE", "local"),
            payload['policy_rule_uri'],
            payload['settings'],
            payload['parameters']
        )

        result = {}
        if mode == "allocate":
            policy_input = prepare_policy_rule_input_for_alloc(block_data)
            result = dry_runner.execute_resource_alloc(policy_input)
        elif mode == "scale":
            policy_input = prepare_policy_rule_input_for_scale(
                block_data['id'], block_data)
            result = dry_runner.execute_for_scale(policy_input)
        else:
            raise Exception(f"invalid mode {mode}")

        node_id = result.get('node_id', None)
        gpus = result.get('gpus', [])

        return node_id, gpus

    except Exception as e:
        raise e


def get_node_id_and_gpus_reassignment(block_data, input_data):
    try:

        block_allocator_policy = block_data.get(
            "policies", {}).get("resourceAllocator", None
                                )

        if not block_allocator_policy:
            raise Exception("block doesn't have a resource allocation policy")

        payload = {
            "block_data": block_data,
            "policy_rule_uri": block_allocator_policy.get("policyRuleURI", "default"),
            "inputs": block_data,
            "parameters": block_allocator_policy.get("parameters", {}),
            "settings": block_allocator_policy.get("settings", {}),
        }

        payload['settings'].update({
            "remove_infra": ""
        })

        # call dry runner:
        dry_runner = DryRunExecutor(
            os.getenv("CLUSTER_DRY_RUN_MODE", "local"),
            payload['policy_rule_uri'],
            payload['settings'],
            payload['parameters']
        )

        result = dry_runner.execute_for_reassignment(input_data)

        if not result:
            return None, None

        node_id = result.get('node_id', None)
        gpus = result.get('gpus', [])

        return node_id, gpus

    except Exception as e:
        raise e


def create_instance(message):
    try:

        # resource allocator:
        node_id, gpus = get_node_id_and_gpus(message)

        block_id = message['id']
        instance_id = 'in-' + generate_unique_alphanumeric_string(4)

        response = BlocksClient().get_block_by_id(block_id)
        if 'error' in response:
            raise Exception(response['error'])

        container_image = response['component']['containerRegistryInfo']['containerImage']

        create_single_instance(block_id, instance_id, container_image, node_id, gpus=gpus)
    except Exception as e:
        logger.error(f"Error creating instance for block: {e}")
        raise


def remove_instance(message):
    try:
        block_id = message['block_id']
        instance_id = message['instance_id']
        remove_single_instance(block_id, instance_id)
    except Exception as e:
        logger.error(
            f"Error removing instance {instance_id} for block {block_id}: {e}")
        raise


def remove_block(message):
    try:
        block_id = message['block_id']

        # remove_executor(block_id)
        time.sleep(5)

        response = BlocksClient().get_block_by_id(block_id)
        if 'error' in response:
            raise Exception(response['error'])

        if InitContainerManager.check_is_init_container(response):
            # create init block:
            ret, resp = InitContainerManager.create_init_container_remove_mode(response)
            if not ret:
                raise Exception(str(resp))
        else:
            remove_deployments_with_blockID(block_id)
            BlocksClient().delete_block_by_id(block_id)

    except Exception as e:
        logger.error(f"Error removing block {block_id}: {e}")
        raise


def scale_instance(message):
    try:

        block_id = message['block_id']

        init_data = message['init_data']

        response = BlocksClient().get_block_by_id(block_id)
        if 'error' in response:
            raise Exception(response['error'])

        instance_id = 'in-' + generate_unique_alphanumeric_string(4)

        node_id, gpus = None, None

        if 'scale_data' in message and message['scale_data']:
            node_id = message['scale_data']['node_id']
            gpus = message['scale_data']['gpu_ids']

        else:
            node_id, gpus = get_node_id_and_gpus(response, mode="scale")

        container_image = response['component']['containerRegistryInfo']['containerImage']

        create_single_instance(block_id, instance_id, container_image, node_id, gpus=gpus, init_data=init_data)

    except Exception as e:
        logger.error(f"Error scaling block: {e}")
        raise


def handle_reassign_instance(message):

    cluster_metrics = ClusterMetricsClient(
        os.getenv("CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000"))
    cluster_metrics.get_cluster_metrics()

    try:
        failed_pods = message['failed_pods']
        for failed_pod in failed_pods:

            if 'executor' in instance_id:
                # executor:
                pass

            instance_id = failed_pod.get('instanceId')
            block_id = failed_pod.get('blockId')

            pod_name = failed_pod.get('pod_name')
            failure_reason = failed_pod.get('failure_reason')
            pod_data = failed_pod.get('pod_data')

            block_data = BlocksClient().get_block_by_id(block_id)
            block_metrics_api = BlockMetricsClient()
            block_metrics = block_metrics_api.get_by_block_id(block_id)
            healthy_nodes = NodesAPIClient().get_healthy_nodes()

            payload = {
                "block": block_data,
                "instance_id": instance_id,
                "cluster": block_data['cluster'],
                "block_metrics": block_metrics,
                "cluster_metrics": cluster_metrics,
                "pod_name": pod_name,
                "pod_data": pod_data,
                "failure_reason": failure_reason,
                "healthy_nodes": healthy_nodes
            }

            remove_single_instance(block_id, instance_id)

            # execute policy rule:
            node_id, gpus = get_node_id_and_gpus_reassignment(
                block_data, payload)
            if not node_id:
                continue

            container_image = block_data['component']['containerRegistryInfo']['containerImage']
            create_single_instance(block_id, instance_id,
                                   container_image, node_id, gpus=gpus)

    except Exception as e:
        logger.error(f"Error scaling bloc: {e}")
        raise


def update_pusher(api_url, parameters):
    try:
        response = requests.post(f"{api_url}/setParameters", json=parameters)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error pushing update to {api_url}: {e}")
        raise


def perform_parameter_update(message):
    try:
        block_id = message['block_id']
        update_data = message.get('update_data', {})
        if not update_data:
            raise Exception("Update data is missing")

        instance_ids = get_all_matching_instances(block_id)
        results = {}

        for instance_id in instance_ids:
            if instance_id != "executor":
                api_url = f"http://{block_id}-{instance_id}-svc.blocks.svc.cluster.local:8001"
                results[instance_id] = update_pusher(api_url, update_data)

        return results
    except Exception as e:
        logger.error(
            f"Error performing parameter update for block {block_id}: {e}")
        raise


def handle_scale_event(payload):
    try:

        if payload['operation'] == 'scale':

            custom_alloc_data = payload.get('allocation_data', [])
            extra_configs = payload.get('init_data', [])

            for idx in range(payload['instances_count']):

                scale_data = None
                extra_config = {}
                if len(custom_alloc_data) > 0:
                    scale_data = custom_alloc_data[idx]

                if len(extra_configs) > 0:
                    extra_config = extra_configs[idx]

                scale_instance({
                    "block_id": payload['block_id'],
                    "scale_data": scale_data,
                    "init_data": extra_config
                })

        elif payload['operation'] == "downscale":
            for instance_id in payload['instances_list']:
                remove_instance({
                    "block_id": payload['block_id'],
                    "instance_id": instance_id,
                })

        return "scaled instances"

    except Exception as e:
        logger.error(f"Error handling scale event: {e}")
        raise


def handle_dry_run(payload):
    try:
        dry_runner = DryRunExecutor(
            os.getenv("CLUSTER_DRY_RUN_MODE", "local"),
            payload['policy_rule_uri'],
            payload['settings'],
            payload['parameters'],
        )

        resource_allocator_input = prepare_policy_rule_input_for_alloc(
            payload['inputs'])

        return dry_runner.execute_dry_run(resource_allocator_input)
    except Exception as e:
        logger.error(f"Error performing dry run: {e}")
        raise


def handle_init_container_status_query(payload):
    try:

        data = InitContainerManager.get_init_container_data(
            payload['block_id'])
        return data

    except Exception as e:
        raise e


def handle_init_container_status(status_data):
    try:
        block_id = status_data.get("block_id")
        status = status_data.get("stage", "unknown")
        data = status_data.get("status_data", {})

        # If status is not "success", set stage to "failed"
        if status_data.get("status") != "success":
            status = "failed"

        # Call InitContainerManager to update the container status
        complete, _ = InitContainerManager.act_on_init_container_status(
            block_id, status, data)
        if complete:
            updated_block = BlocksClient().update_block_by_id(block_id, {
                "$set": {
                    "blockInitData.initContainer": data
                }
            })

            if 'error' in updated_block:
                raise Exception(updated_block['error'])

            # create a new executor and single instance:
            block_data = updated_block
            node_port = create_executor(block_id, namespace="blocks")

            updated_block = BlocksClient().update_block_by_id(block_id, {
                "$set": {
                    "blockInitData.external_port": node_port
                }
            })

            # min instances:
            create_instance(block_data)

            time.sleep(5)
            register_health_checker(block_id, block_data)

            # perform de-init tasks:
            InitContainerManager.remove_init_container(block_id)

            return "status updated"

        else:
            return "status updated"

    except Exception as e:
        logger.error(f"Error handling init container status: {str(e)}")
        return False, str(e)


def handle_init_remove_container_status(status_data):
    try:
        block_id = status_data.get("block_id")
        status = status_data.get("stage", "unknown")
        data = status_data.get("status_data", {})

        # If status is not "success", set stage to "failed"
        if status_data.get("status") != "success":
            status = "failed"

        # Call InitContainerManager to update the container status
        complete, _ = InitContainerManager.act_on_init_container_status(
            block_id, status, data)
        if complete:

            # init block removal:
            remove_deployments_with_blockID(block_id)
            BlocksClient().delete_block_by_id(block_id)

            # remove init container:
            InitContainerManager.remove_init_container(block_id)

        else:
            return "status updated"

    except Exception as e:
        logger.error(f"Error handling init container status: {str(e)}")
        return False, str(e)


def run_handle_reassign_instance_in_thread(message):
    try:
        message_copy = copy.deepcopy(message)
        thread = threading.Thread(
            target=handle_reassign_instance, args=(message_copy,))
        thread.start()
        # Optional: return the thread in case you want to join/wait
        return "started re-assignment"
    except Exception as e:
        logger.error(
            f"Failed to start thread for handle_reassign_instance: {e}")
        raise


class Router:
    def __init__(self, message):
        self.message = message

    def _check_cluster(self):
        return self.message['cluster_id'] == os.getenv("CLUSTER_ID")

    def route(self):
        try:
            action = self.message['action']
            if action == "remove_block":
                return remove_block(self.message)
            elif action == "create_block":
                return create_block(self.message)
            elif action == "parameter_update":
                return perform_parameter_update(self.message)
            elif action == "scale":
                return handle_scale_event(self.message)
            elif action == "dry_run":
                return handle_dry_run(self.message)
            elif action == "remove_instance":
                return remove_instance(self.message)
            elif action == "init_create_status_update":
                return handle_init_container_status(self.message)
            elif action == "init_remove_status_update":
                return handle_init_remove_container_status(self.message)
            elif action == "query_init_container_data":
                return handle_init_container_status_query(self.message)
            elif action == "failed_pods":
                return run_handle_reassign_instance_in_thread(self.message)
            else:
                raise Exception(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            raise
