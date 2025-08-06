import requests
import os

from .db import ExecutorsDB


class ResourceAllocatorClient:
    def __init__(self):

        self.base_url = os.getenv("RESOURCE_ALLOCATOR_API_URL", "http://localhost:7777")

    def allocate_resources(self, policy_rule_uri: str, clusters: list, inputs: dict, parameters: dict = None, settings: dict = None):

        url = f"{self.base_url}/allocate"
        payload = {
            "policy_rule_uri": policy_rule_uri,
            "clusters": clusters,
            "inputs": inputs,
            "parameters": parameters or {},
            "settings": settings or {}
        }

        response = requests.post(url, json=payload)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("success", False):
            return response_data["data"]
        else:
            raise Exception(response_data.get(
                "message", "Unknown error occurred"))


def alloc_resource_func(resource_allocator_policy_uri: str, settings: dict, parameters: dict):
    try:

        executors = ExecutorsDB()
        docs = executors.query({})

        clusters = []
        for doc in docs:
            cluster_id = doc.executor_hardware_info['clusterId']
            clusters.append(cluster_id)

        resource_alloc = ResourceAllocatorClient()
        response = resource_alloc.allocate_resources(
            resource_allocator_policy_uri, clusters=clusters, settings=settings, parameters=parameters, inputs={
                "mode": "function"
            }
        )

        cluster_id = response['clusterId']
        replicas = response.get('replica_count', 1)

        return cluster_id, replicas

    except Exception as e:
        raise e


def alloc_resource_job(resource_allocator_policy_uri: str, settings: dict, parameters: dict):
    try:

        executors = ExecutorsDB()
        docs = executors.query({})

        clusters = []
        for doc in docs:
            cluster_id = doc.executor_hardware_info['clusterId']
            clusters.append(cluster_id)

        resource_alloc = ResourceAllocatorClient()
        response = resource_alloc.allocate_resources(
            resource_allocator_policy_uri, clusters=clusters, settings=settings, parameters=parameters, inputs={
                "mode": "job"
            }
        )

        cluster_id = response['clusterId']
        replicas = response.get('replica_count', 1)

        return cluster_id, replicas

    except Exception as e:
        raise e
