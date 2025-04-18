import redis
import json
import time
import logging
from datetime import datetime
from pymongo import MongoClient, errors
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskUpdater:
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

    def update_task_status(self, task_id: str, status: str, task_status_data: dict):
        update_fields = {
            "task_status": status,
            "task_status_data": task_status_data,
            "task_update_timestamp": int(time.time())
        }

        return self.update(task_id, update_fields)

class UpdatesRedisConsumer:
    def __init__(self, queue_name="TASK_UPDATES"):
        self.queue_name = queue_name
        self.redis_client = None
        self.task_updater = TaskUpdater()
        self.connect_to_redis()

    def connect_to_redis(self):
        while True:
            try:
                self.redis_client = redis.StrictRedis(
                    host='localhost', port=6379, db=0, decode_responses=True)
                if self.redis_client.ping():
                    logger.info("Connected to Redis successfully.")
                    break
            except redis.ConnectionError as e:
                logger.error(
                    f"Redis connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def listen_for_updates(self):
        logger.info(f"Listening for messages on queue: {self.queue_name}")
        while True:
            try:
                message = self.redis_client.blpop(self.queue_name)
                if message:
                    _, data = message
                    update = json.loads(data)
                    self.process_update(update)
            except (redis.ConnectionError, json.JSONDecodeError) as e:
                logger.error(f"Error processing update: {e}")
                self.connect_to_redis()

    def process_update(self, update):
        try:
            logger.info(f"Received update: {update}")
            task_id = update.get("task_id")
            status = update.get("status")
            task_status_data = update.get("task_status_data", {})
            if task_id and status:
                self.task_updater.update_task_status(task_id, status, task_status_data)
            else:
                logger.warning("Invalid update format received.")
        except Exception as e:
            raise e


def start_listener():
    while True:
        try:
            consumer = UpdatesRedisConsumer()
            consumer.listen_for_updates()
        except Exception as e:
            logger.error("[fail_to_listen]: " + str(e))
