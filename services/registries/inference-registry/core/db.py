import logging
import os
from pymongo import MongoClient, errors
from typing import Dict, List, Tuple, Union
from .schema import InferenceServer 

logger = logging.getLogger(__name__)

class InferenceServerDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["inference"]
            self.collection = self.db["inference_servers"]
            logger.info("MongoDB connection established for InferenceServerDatabase")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, inference_server: InferenceServer) -> Tuple[bool, Union[str, None]]:
        try:
            document = inference_server.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"InferenceServer inserted with ID: {inference_server.inference_server_id}")
            return True, str(result.inserted_id)
        except errors.PyMongoError as e:
            logger.error(f"Error inserting inference server: {e}")
            return False, str(e)

    def update(self, inference_server_id: str, update_fields: Dict) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.update_one(
                {"inference_server_id": inference_server_id},
                update_fields,
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"InferenceServer with ID {inference_server_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with ID {inference_server_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating inference server: {e}")
            return False, str(e)

    def delete(self, inference_server_id: str) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.delete_one({"inference_server_id": inference_server_id})
            if result.deleted_count > 0:
                logger.info(f"InferenceServer with ID {inference_server_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with ID {inference_server_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting inference server: {e}")
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
            logger.error(f"Error querying inference servers: {e}")
            return False, str(e)

    def get_by_inference_server_id(self, inference_server_id: str) -> Tuple[bool, Union[InferenceServer, str]]:
        try:
            doc = self.collection.find_one({"inference_server_id": inference_server_id})
            if doc:
                doc.pop('_id', None)
                inference_server = InferenceServer.from_dict(doc)
                logger.info(f"InferenceServer with ID {inference_server_id} retrieved")
                return True, inference_server
            else:
                logger.info(f"No inference server found with ID {inference_server_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving inference server: {e}")
            return False, str(e)
