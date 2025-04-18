import os
import logging

from typing import Tuple, Union, Dict, Any, List
from pymongo import MongoClient, errors
from .schema import vDAGObject, vDAGController

logger = logging.getLogger(__name__)


class VDAGDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["vdags"]
            self.collection = self.db["vdags"]
            logger.info("MongoDB connection established")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, vdag: vDAGObject):
        try:
            document = vdag.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"vDAG inserted with vdagURI: {vdag.vdagURI}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting vDAG: {e}")
            return False, str(e)

    def update(self, vdagURI: str, update_fields: dict):
        try:
            result = self.collection.update_one(
                {"vdagURI": vdagURI},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"vDAG with vdagURI {vdagURI} updated")
                return True, result.modified_count
            else:
                logger.info(
                    f"No document found with vdagURI {vdagURI} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating vDAG: {e}")
            return False, str(e)

    def delete(self, vdagURI: str):
        try:
            result = self.collection.delete_one({"vdagURI": vdagURI})
            if result.deleted_count > 0:
                logger.info(f"vDAG with vdagURI {vdagURI} deleted")
                return True, result.deleted_count
            else:
                logger.info(
                    f"No document found with vdagURI {vdagURI} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting vDAG: {e}")
            return False, str(e)

    def query(self, query_filter: dict):
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying vDAGs: {e}")
            return False, str(e)

    def get_by_vdagURI(self, vdagURI: str):
        try:
            doc = self.collection.find_one({"vdagURI": vdagURI})
            if doc:
                doc.pop('_id', None)
                vdag = vDAGObject.from_dict(doc)
                logger.info(f"vDAG with vdagURI {vdagURI} retrieved")
                return True, vdag
            else:
                logger.info(f"No vDAG found with vdagURI {vdagURI}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving vDAG: {e}")
            return False, str(e)


class VDAGControllerDB:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["vdags"]
            self.collection = self.db["vdag_controllers"]
            logger.info("MongoDB connection established for vDAGControllerDB")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, vdag_controller: vDAGController) -> Tuple[bool, Union[str, Any]]:
        try:
            document = vdag_controller.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"vDAGController inserted with ID: {vdag_controller.vdag_controller_id}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting vDAGController: {e}")
            return False, str(e)

    def update(self, vdag_controller_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.update_one(
                {"vdag_controller_id": vdag_controller_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"vDAGController with ID {vdag_controller_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with ID {vdag_controller_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating vDAGController: {e}")
            return False, str(e)

    def delete(self, vdag_controller_id: str) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.delete_one({"vdag_controller_id": vdag_controller_id})
            if result.deleted_count > 0:
                logger.info(f"vDAGController with ID {vdag_controller_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with ID {vdag_controller_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting vDAGController: {e}")
            return False, str(e)

    def query(self, query_filter: Dict[str, Any]) -> Tuple[bool, Union[str, List[Dict[str, Any]]]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying vDAGControllers: {e}")
            return False, str(e)

    def get_by_id(self, vdag_controller_id: str) -> Tuple[bool, Union[str, vDAGController]]:
        try:
            doc = self.collection.find_one({"vdag_controller_id": vdag_controller_id})
            if doc:
                doc.pop('_id', None)
                vdag_controller = vDAGController.from_dict(doc)
                logger.info(f"vDAGController with ID {vdag_controller_id} retrieved")
                return True, vdag_controller
            else:
                logger.info(f"No vDAGController found with ID {vdag_controller_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving vDAGController: {e}")
            return False, str(e)

    def list_by_vdag_uri(self, vdag_uri: str) -> Tuple[bool, Union[str, List[vDAGController]]]:
        try:
            result = self.collection.find({"vdag_uri": vdag_uri})
            controllers = []
            for doc in result:
                doc.pop('_id', None)
                controllers.append(vDAGController.from_dict(doc))
            logger.info(f"Found {len(controllers)} vDAGControllers for vdag_uri: {vdag_uri}")
            return True, controllers
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving vDAGControllers for vdag_uri {vdag_uri}: {e}")
            return False, str(e)