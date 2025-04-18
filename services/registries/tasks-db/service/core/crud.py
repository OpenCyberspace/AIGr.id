import os
import logging
from pymongo import MongoClient, errors
from datetime import datetime
from .schema import GlobalTask

logger = logging.getLogger(__name__)

class GlobalTasksDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["tasks"]
            self.collection = self.db["global_tasks"]
            logger.info("MongoDB connection established")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, task: GlobalTask):
        try:
            task.task_create_timestamp = int(datetime.utcnow().timestamp())
            task.task_update_timestamp = task.task_create_timestamp
            document = task.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Task inserted with task_id: {task.task_id}")
            return True, task.task_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting task: {e}")
            return False, str(e)

    def update(self, task_id: str, update_fields: dict):
        try:
            update_fields["task_update_timestamp"] = int(datetime.utcnow().timestamp())
            result = self.collection.update_one(
                {"task_id": task_id},
                {"$set": update_fields},
                upsert=False
            )
            if result.modified_count > 0:
                logger.info(f"Task with task_id {task_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with task_id {task_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating task: {e}")
            return False, str(e)

    def delete(self, task_id: str):
        try:
            result = self.collection.delete_one({"task_id": task_id})
            if result.deleted_count > 0:
                logger.info(f"Task with task_id {task_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with task_id {task_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting task: {e}")
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
            logger.error(f"Error querying tasks: {e}")
            return False, str(e)

    def get_by_task_id(self, task_id: str):
        try:
            doc = self.collection.find_one({"task_id": task_id})
            if doc:
                doc.pop('_id', None)
                task = GlobalTask.from_dict(doc)
                logger.info(f"Task with task_id {task_id} retrieved")
                return True, task
            else:
                logger.info(f"No task found with task_id {task_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving task: {e}")
            return False, str(e)

    def get_tasks_by_task_type(self, task_type: str, task_status: str = None):
        try:
            query_filter = {"task_type": task_type}
            if task_status:
                query_filter["task_status"] = task_status
            
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            
            logger.info(f"Query successful, found {len(documents)} tasks with task_type {task_type}")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying tasks by task_type: {e}")
            return False, str(e)
