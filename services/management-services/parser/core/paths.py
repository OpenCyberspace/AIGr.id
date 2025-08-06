import logging
import json
import requests
import os

from .utils import generate_unique_alphanumeric_string

from .async_pool import ThreadPoolQueueSystem
from .modules.similarity_search import SearchServerAPI
from .modules.llm_planner import LLMVDAGCreator
from .modules.block_actions import execute_cluster_dry_run, execute_block_allocation, execute_block_selection, execute_vdag_allocation
from .modules.cluster_actions import ClusterInfraManagement
from .modules.vdag import vDAGProcessingAPI, vDAGDryRunAPIs
from .webhooks.parameter_updater import ParameterUpdater
import time
import random

max_pool_size = int(os.getenv("MAX_WORKER_POOL_SIZE", "50"))
thread_pool = ThreadPoolQueueSystem(max_workers=max_pool_size)


def create_cluster_path(ir: dict):
    # generate a cluster ID:
    try:

        # call DB API to create the cluster:
        cluster_service = ClusterInfraManagement()

        resp = cluster_service.create_cluster(ir)
        return resp

    except Exception as e:
        return False, str(e)


def add_node_to_cluster_path(ir: dict):
    # generate a cluster ID:
    try:

        cluster_id = ir['clusterId']
        node_data = ir['nodeData']

        # call DB API to create the cluster:
        cluster_service = ClusterInfraManagement()

        resp = cluster_service.add_node_to_cluster(cluster_id, node_data)
        return resp

    except Exception as e:
        return False, str(e)


def filter_path(ir: dict):
    try:

        search = SearchServerAPI()
        return search.filter_search(ir['matchType'], ir['filter'])

    except Exception as e:
        return False, str(e)


def similarity_search_path(ir: dict):
    try:

        rankingPolicyRule = ir['rankingPolicyRule']
        search_server = SearchServerAPI()
        response = search_server.similarity_search(
            rankingPolicyRule['policyRuleURI'], rankingPolicyRule['parameters'])
        return True, response

    except Exception as e:
        return False, str(e)


def similarity_search_executor_path(ir: dict):
    try:

        rankingPolicyRule = ir['rankingPolicyRule']
        search_server = SearchServerAPI()
        response = search_server.similarity_search(
            rankingPolicyRule['policyRuleURI'], rankingPolicyRule['parameters'])
        return True, response

    except Exception as e:
        return False, str(e)


def block_action_path(ir: dict):
    try:

        print(ir)
        mode = ir.get("api_mode")

        if mode == "select_clusters":
            return execute_block_selection(ir)

        elif mode == "allocate":
            return execute_block_allocation(ir)

        elif mode == "dry_run":
            return execute_cluster_dry_run(ir)

        else:
            raise Exception(f"Invalid block api mode: {mode}")

    except Exception as e:
        print(f"Error in block_action_path: {e}")
        raise e


def create_llm_vdag(ir: dict):
    try:

        llm_creator = LLMVDAGCreator()
        llm_creator.create_llm_vdag(ir)

    except Exception as e:
        raise e


def create_vdag(ir: dict):
    try:
        mode = ir['mode']

        if mode == "create":
            processor = vDAGProcessingAPI()

            del ir['mode']
            return processor.submit_task(ir)

        if mode == "validateGraph":
            dry_runner = vDAGDryRunAPIs()

            del ir['mode']
            return dry_runner.validate_graph(ir)

        if mode == "dryRunAssignment":
            dry_runner = vDAGDryRunAPIs()

            del ir['mode']
            return dry_runner.dryrun_assignment_policy(ir)

        if mode == "dryRun":
            dry_runner = vDAGDryRunAPIs()

            del ir['mode']
            return dry_runner.dryrun_end_to_end(ir)

        raise Exception(f"invalid mode: {e}")

    except Exception as e:
        raise e


def execute_mgmt_command_path(ir: dict):
    try:
        parameter_updater = ParameterUpdater()

        block_id = ir['blockId']
        service = ir['service']
        mgmt_command = ir['mgmtCommand']
        mgmt_data = ir['mgmtData']
        cluster_id = ir['clusterId']
        instance_id = ir['instanceId']

        return parameter_updater.update_parameters(cluster_id, block_id, service, mgmt_command, mgmt_data, instance_id)

    except Exception as e:
        raise e
