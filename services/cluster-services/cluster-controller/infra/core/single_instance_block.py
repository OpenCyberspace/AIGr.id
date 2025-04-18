from dataclasses import dataclass, field
from typing import Dict, Any, Tuple
import uuid
import redis
import json
from pymongo import MongoClient, errors

from .k8s import create_init_block, delete_init_block

import os

import logging

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
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            block_data=data.get('block_data', {}),
            status=data.get('status', ''),
            status_data=data.get('status_data', {})
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
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = redis.from_url(redis_url, decode_responses=True)

    def create(self, container: InitContainerEntry) -> Tuple[bool, str]:
        try:
            container_id = f"init__{container.id}"
            self.client.set(container_id, json.dumps(container.to_dict()))
            return True, container_id
        except redis.RedisError as e:
            return False, str(e)

    def get_by_id(self, container_id: str) -> Tuple[bool, Any]:
        try:
            container_id = f"init__{container_id}"
            data = self.client.get(container_id)
            if data:
                return True, InitContainerEntry.from_dict(json.loads(data))
            return False, "No document found"
        except redis.RedisError as e:
            return False, str(e)

    def update(self, container_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            container_id = f"init__{container_id}"
            data = self.client.get(container_id)
            if data:
                container_data = json.loads(data)
                container_data.update(update_fields)
                self.client.set(container_id, json.dumps(container_data))
                return True, "Updated successfully"
            return False, "No document found"
        except redis.RedisError as e:
            return False, str(e)

    def delete(self, container_id: str) -> Tuple[bool, str]:
        try:
            container_id = f"init__{container_id}"
            deleted = self.client.delete(container_id)
            if deleted:
                return True, "Deleted successfully"
            return False, "No document found"
        except redis.RedisError as e:
            return False, str(e)


def is_init_container(block_data: dict):
    try:
        component_data = block_data['component']
        if component_data.get('componentMode', "aios") != "third_party":
            return True
        return False
    except Exception as e:
        raise e


def get_init_container_image_name(block_data: dict):
    try:
        component_data = block_data['component']
        init_container = component_data.get('initContainer', None)
        if not init_container:
            raise Exception("init container data not found in component")

        image = init_container['image']

        return image

    except Exception as e:
        raise e


class InitContainerManager:

    @staticmethod
    def check_is_init_container(block_data: dict):
        return is_init_container(block_data)

    @staticmethod
    def create_init_container(block_data: dict):
        try:
            block_id = block_data['id']
            image_name = get_init_container_image_name(block_data)

            # 1. Create an entry in Redis using InitContainersDB
            container_entry = InitContainerEntry(
                id=block_id, block_data=block_data, status="pending", status_data={})
            db = InitContainersDB()
            success, msg = db.create(container_entry)

            if not success:
                raise Exception(f"Failed to create InitContainer entry: {msg}")

            # 2. Create the init container using Kubernetes
            create_init_block(block_id, image_name)

            # 3. Return success message
            logger.info(f"Init container {block_id} created successfully")
            return True, f"Init container {block_id} created successfully"

        except Exception as e:
            logger.error(f"Error in creating init container: {str(e)}")
            return False, str(e)

    @staticmethod
    def act_on_init_container_status(id: str, status: str, status_data: dict):
        try:
            db = InitContainersDB()

            # 1. Fetch the existing init container entry
            success, container = db.get_by_id(id)
            if not success:
                raise Exception(f"Failed to fetch InitContainer: {container}")

            # 2. Update the status and status_data
            update_fields = {
                "status": status,
                "status_data": status_data
            }
            success, msg = db.update(id, update_fields)
            if not success:
                raise Exception(f"Failed to update InitContainer: {msg}")

            logger.info(f"Updated InitContainer {id} status to {status}")
            if status == "finish":
                return True, status_data
            else:
                return False, None

        except Exception as e:
            logger.error(f"Error in updating init container status: {str(e)}")
            raise e

    @staticmethod
    def get_init_container_data(id: str):
        try:
            db = InitContainersDB()

            # Fetch the container entry
            success, container = db.get_by_id(id)
            if not success:
                raise Exception(f"Failed to fetch InitContainer: {container}")

            logger.info(f"Fetched InitContainer data for {id}")
            return True, container.to_dict()

        except Exception as e:
            logger.error(f"Error in fetching init container data: {str(e)}")
            return False, str(e)

    @staticmethod
    def remove_init_container(block_id: str):
        try:
            # 1. Remove the entry from Redis using InitContainersDB
            db = InitContainersDB()
            success, msg = db.delete(block_id)

            if not success:
                raise Exception(f"Failed to delete InitContainer entry: {msg}")

            # 2. Remove the init container using Kubernetes
            delete_init_block(block_id)

            # 3. Return success message
            logger.info(f"Init container {block_id} removed successfully")
            return True, f"Init container {block_id} removed successfully"

        except Exception as e:
            logger.error(f"Error in removing init container: {str(e)}")
            return False, str(e)
