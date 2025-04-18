import os
import logging
from typing import Dict, List, Tuple, Union
from pymongo import MongoClient, errors

from .schema import ContainerRegistry  

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ContainerRegistryDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["assets"]
            self.collection = self.db["container_registry"]
            logger.info("MongoDB connection established for ContainerRegistryDatabase")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, container_registry: ContainerRegistry) -> Tuple[bool, Union[str, None]]:
        try:
            document = container_registry.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"ContainerRegistry inserted with ID: {container_registry.container_registry_id}")
            return True, str(result.inserted_id)
        except errors.PyMongoError as e:
            logger.error(f"Error inserting container registry: {e}")
            return False, str(e)

    def update(self, container_registry_id: str, update_fields: Dict) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.update_one(
                {"container_registry_id": container_registry_id},
                update_fields,
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"ContainerRegistry with ID {container_registry_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with ID {container_registry_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating container registry: {e}")
            return False, str(e)

    def delete(self, container_registry_id: str) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.delete_one({"container_registry_id": container_registry_id})
            if result.deleted_count > 0:
                logger.info(f"ContainerRegistry with ID {container_registry_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with ID {container_registry_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting container registry: {e}")
            return False, str(e)

    def query(self, query_filter: Dict) -> Tuple[bool, Union[List[Dict], str]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying container registries: {e}")
            return False, str(e)

    def get_by_container_registry_id(self, container_registry_id: str) -> Tuple[bool, Union[ContainerRegistry, str]]:
        try:
            doc = self.collection.find_one({"container_registry_id": container_registry_id})
            if doc:
                doc.pop('_id', None)
                container_registry = ContainerRegistry.from_dict(doc)
                logger.info(f"ContainerRegistry with ID {container_registry_id} retrieved")
                return True, container_registry
            else:
                logger.info(f"No container registry found with ID {container_registry_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving container registry: {e}")
            return False, str(e)
