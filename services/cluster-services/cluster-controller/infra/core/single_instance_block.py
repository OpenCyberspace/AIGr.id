from dataclasses import dataclass, field
from typing import Dict, Any, Tuple
import uuid
import redis
import json
import os
import logging
import copy

from .cluster_db import ClusterClient
from .metrics import ClusterMetricsClient
from .nodes_api import NodesAPIClient
from .k8s import create_init_block, delete_init_block, create_init_block_remove_mode
from .dry_runner import DryRunExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class InitContainerEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    block_data: Dict[str, Any] = field(default_factory=dict)
    status_data: Dict[str, Any] = field(default_factory=dict)
    status: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InitContainerEntry':
        block_data = data.get('block_data', {})
        status_data = data.get('status_data', {})

        if not isinstance(block_data, dict):
            raise ValueError("block_data must be a dict")

        return cls(
            id=data.get('id', str(uuid.uuid4())),
            block_data=block_data,
            status=data.get('status', ''),
            status_data=status_data
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'block_data': self.block_data,
            'status': self.status,
            'status_data': self.status_data
        }


class InitContainersDB:
    def __init__(self):
        redis_url = "redis://localhost:6379"
        self.client = redis.from_url(redis_url, decode_responses=True)

    def _prefix_id(self, container_id: str) -> str:
        return container_id if container_id.startswith("init__") else f"init__{container_id}"

    def create(self, container: InitContainerEntry) -> Tuple[bool, str]:
        try:
            container_id = self._prefix_id(container.id)
            logger.info(f"[init_container_key]: {container_id} value: {container.to_dict()}")
            self.client.set(container_id, json.dumps(container.to_dict()))
            return True, container_id
        except redis.RedisError as e:
            return False, str(e)

    def get_by_id(self, container_id: str) -> Tuple[bool, Any]:
        try:
            key = self._prefix_id(container_id)
            logger.info(f"[init_container_key]: {key}")
            data = self.client.get(key)
            if data:
                return True, InitContainerEntry.from_dict(json.loads(data))
            return False, "No document found"
        except redis.RedisError as e:
            return False, str(e)

    def update(self, container_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            key = self._prefix_id(container_id)
            data = self.client.get(key)
            if data:
                container_data = json.loads(data)
                container_data.update(update_fields)
                self.client.set(key, json.dumps(container_data))
                return True, "Updated successfully"
            return False, "No document found"
        except redis.RedisError as e:
            return False, str(e)

    def delete(self, container_id: str) -> Tuple[bool, str]:
        try:
            key = self._prefix_id(container_id)
            deleted = self.client.delete(key)
            if deleted:
                return True, "Deleted successfully"
            return False, "No document found"
        except redis.RedisError as e:
            return False, str(e)


def is_init_container(block_data: dict) -> bool:

    logger.info(f"checking init container status: [{block_data}]")
    component_data = block_data.get(
        'component', {}).get('containerRegistryInfo', {})
    return component_data.get('componentMode', "aios") == "third_party"


def get_init_container_image_name(block_data: dict) -> str:
    component_data = block_data.get(
        'component', {}).get('containerRegistryInfo', {})
    init_container = component_data.get('initContainer')
    if not init_container:
        raise ValueError("init container data not found in component")
    return init_container['image']


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


class InitContainerManager:

    @staticmethod
    def check_is_init_container(block_data: dict) -> bool:
        return is_init_container(block_data)

    @staticmethod
    def create_init_container_remove_mode(block_data: dict):
        try:

            block_data_copy = copy.deepcopy(block_data)
            container_entry = InitContainerEntry(
                id=block_data['id'],
                block_data=block_data_copy,  # Use safe version
                status="pending",
                status_data={}
            )

            db = InitContainersDB()
            success, msg = db.create(container_entry)

            if not success:
                raise RuntimeError(f"Failed to create InitContainer entry: {msg}")

            # get image name:
            image_name = get_init_container_image_name(block_data)
            
            create_init_block_remove_mode(block_id=block_data['id'], image_name=image_name)

            logger.info(f"Init container {block_data['id']} created successfully in 'remove' mode")
            return True, f"Init container {block_data['id']} created successfully in 'remove' mode"

        except Exception as e:
            return False, str(e)

    
    @staticmethod
    def create_init_container(block_data: dict) -> Tuple[bool, str]:
        try:
            block_id = block_data['id']
            image_name = get_init_container_image_name(block_data)

            block_allocator_policy = block_data.get(
                "policies", {}).get("resourceAllocator", None)
            if not block_allocator_policy:
                raise Exception("block doesn't have a resource allocation policy")

            # Use deep copy to avoid side effects
            safe_block_data = copy.deepcopy(block_data)

            policy_rule_uri = block_allocator_policy.get(
                "policyRuleURI", "default")
            settings = block_allocator_policy.get("settings", {})
            parameters = block_allocator_policy.get("parameters", {})

            dry_runner = DryRunExecutor(
                os.getenv("CLUSTER_DRY_RUN_MODE", "local"),
                policy_rule_uri,
                settings,
                parameters
            )

            input_data = prepare_policy_rule_input_for_alloc(safe_block_data)
            result = dry_runner.execute_for_init_container(input_data)

            container_entry = InitContainerEntry(
                id=block_id,
                block_data=safe_block_data,  # Use safe version
                status="pending",
                status_data={}
            )

            logger.info(f"init container data: {container_entry.to_dict()}")

            db = InitContainersDB()
            success, msg = db.create(container_entry)

            if not success:
                raise RuntimeError(f"Failed to create InitContainer entry: {msg}")

            create_init_block(block_id, image_name, result)

            logger.info(f"Init container {block_id} created successfully")
            return True, f"Init container {block_id} created successfully"

        except Exception as e:
            logger.exception(f"Error in creating init container")
            return False, str(e)

    @staticmethod
    def act_on_init_container_status(id: str, status: str, status_data: dict) -> Tuple[bool, Any]:
        try:
            db = InitContainersDB()

            success, container = db.get_by_id(id)
            if not success:
                raise RuntimeError(
                    f"Failed to fetch InitContainer: {container}")

            update_fields = {
                "status": status,
                "status_data": status_data
            }
            success, msg = db.update(id, update_fields)
            if not success:
                raise RuntimeError(f"Failed to update InitContainer: {msg}")

            logger.info(f"Updated InitContainer {id} status to {status}")
            return (True, status_data) if status == "finish" else (False, None)

        except Exception as e:
            logger.exception(f"Error in updating init container status")
            raise

    @staticmethod
    def get_init_container_data(id: str) -> Tuple[bool, Any]:
        try:
            db = InitContainersDB()
            success, container = db.get_by_id(id)
            if not success:
                raise RuntimeError(
                    f"Failed to fetch InitContainer: {container}")

            logger.info(f"Fetched InitContainer data for {id}")
            return True, container.to_dict()

        except Exception as e:
            logger.exception(f"Error in fetching init container data")
            return False, str(e)

    @staticmethod
    def remove_init_container(block_id: str) -> Tuple[bool, str]:
        try:
            db = InitContainersDB()
            success, msg = db.delete(block_id)

            if not success:
                raise RuntimeError(
                    f"Failed to delete InitContainer entry: {msg}")

            delete_init_block(block_id)

            logger.info(f"Init container {block_id} removed successfully")
            return True, f"Init container {block_id} removed successfully"

        except Exception as e:
            logger.exception(f"Error in removing init container")
            return False, str(e)
