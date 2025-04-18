import os
import logging
from typing import Tuple, Union, List, Dict
from pymongo import MongoClient, errors
from .schema import AssetRegistry

logger = logging.getLogger(__name__)

class AssetRegistryDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["assets"]
            self.collection = self.db["asset_registry"]
            logger.info("MongoDB connection established for AssetRegistryDatabase")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, asset_registry: AssetRegistry) -> Tuple[bool, Union[str, None]]:
        try:
            document = asset_registry.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"AssetRegistry inserted with ID: {asset_registry.asset_registry_id}")
            return True, str(result.inserted_id)
        except errors.PyMongoError as e:
            logger.error(f"Error inserting asset registry: {e}")
            return False, str(e)

    def update(self, asset_registry_id: str, update_fields: Dict) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.update_one(
                {"asset_registry_id": asset_registry_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"AssetRegistry with ID {asset_registry_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with ID {asset_registry_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating asset registry: {e}")
            return False, str(e)

    def delete(self, asset_registry_id: str) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.delete_one({"asset_registry_id": asset_registry_id})
            if result.deleted_count > 0:
                logger.info(f"AssetRegistry with ID {asset_registry_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with ID {asset_registry_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting asset registry: {e}")
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
            logger.error(f"Error querying asset registries: {e}")
            return False, str(e)

    def get_by_asset_registry_id(self, asset_registry_id: str) -> Tuple[bool, Union[AssetRegistry, str]]:
        try:
            doc = self.collection.find_one({"asset_registry_id": asset_registry_id})
            if doc:
                doc.pop('_id', None)
                asset_registry = AssetRegistry.from_dict(doc)
                logger.info(f"AssetRegistry with ID {asset_registry_id} retrieved")
                return True, asset_registry
            else:
                logger.info(f"No asset registry found with ID {asset_registry_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving asset registry: {e}")
            return False, str(e)
