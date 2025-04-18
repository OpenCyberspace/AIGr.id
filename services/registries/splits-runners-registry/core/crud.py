import os
import logging
from pymongo import MongoClient, errors
from typing import Dict, Any, List, Tuple
from .schema import SplitRunnerObject 

logger = logging.getLogger(__name__)


class SplitRunnerDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["split_runner_store"]
            self.collection = self.db["split_runners"]
            logger.info("MongoDB connection established for SplitRunner")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, runner: SplitRunnerObject) -> Tuple[bool, Any]:
        try:
            document = runner.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"SplitRunner inserted with ID: {runner.split_runner_id}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting SplitRunner: {e}")
            return False, str(e)

    def update(self, runner_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.update_one(
                {"split_runner_id": runner_id},
                update_fields,
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"SplitRunner with ID {runner_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with ID {runner_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating SplitRunner: {e}")
            return False, str(e)

    def delete(self, runner_id: str) -> Tuple[bool, Any]:
        try:
            result = self.collection.delete_one({"split_runner_id": runner_id})
            if result.deleted_count > 0:
                logger.info(f"SplitRunner with ID {runner_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with ID {runner_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting SplitRunner: {e}")
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
            logger.error(f"Error querying SplitRunners: {e}")
            return False, str(e)

    def get_by_runner_id(self, runner_id: str) -> Tuple[bool, Any]:
        try:
            doc = self.collection.find_one({"split_runner_id": runner_id})
            if doc:
                doc.pop('_id', None)
                runner = SplitRunnerObject.from_dict(doc)
                logger.info(f"SplitRunner with ID {runner_id} retrieved")
                return True, runner
            else:
                logger.info(f"No SplitRunner found with ID {runner_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving SplitRunner: {e}")
            return False, str(e)
