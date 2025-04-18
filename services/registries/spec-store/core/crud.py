import os
import logging
from pymongo import MongoClient, errors
from typing import Dict, Any, List, Tuple
from .schema import SpecStoreObject

logger = logging.getLogger(__name__)


class SpecStoreDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["spec_store"]
            self.collection = self.db["specs"]
            logger.info("MongoDB connection established for SpecStore")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, spec: SpecStoreObject) -> Tuple[bool, Any]:
        try:
            document = spec.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Spec inserted with specUri: {spec.specUri}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting Spec: {e}")
            return False, str(e)

    def update(self, specUri: str, update_fields: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.update_one(
                {"specUri": specUri},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Spec with specUri {specUri} updated")
                return True, result.modified_count
            else:
                logger.info(
                    f"No document found with specUri {specUri} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating Spec: {e}")
            return False, str(e)

    def delete(self, specUri: str) -> Tuple[bool, Any]:
        try:
            result = self.collection.delete_one({"specUri": specUri})
            if result.deleted_count > 0:
                logger.info(f"Spec with specUri {specUri} deleted")
                return True, result.deleted_count
            else:
                logger.info(
                    f"No document found with specUri {specUri} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting Spec: {e}")
            return False, str(e)

    def query(self, query_filter: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying Specs: {e}")
            return False, str(e)

    def get_by_specUri(self, specUri: str) -> Tuple[bool, Any]:
        try:
            doc = self.collection.find_one({"specUri": specUri})
            if doc:
                doc.pop('_id', None)
                spec = SpecStoreObject.from_dict(doc)
                logger.info(f"Spec with specUri {specUri} retrieved")
                return True, spec
            else:
                logger.info(f"No Spec found with specUri {specUri}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving Spec: {e}")
            return False, str(e)
