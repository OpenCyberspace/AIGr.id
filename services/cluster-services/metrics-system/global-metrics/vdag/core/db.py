import os
import json
import time
import threading
import logging
import redis
from pymongo import MongoClient, errors

# Logger setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class VDAGMetrics:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["vdag_metrics"]
            self.collection = self.db["vdag_metrics"]
            logger.info("MongoDB connection established")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, document):
        try:
            result = self.collection.insert_one(document)
            logger.info(f"Document inserted with ID: {result.inserted_id}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting document: {e}")
            return False, str(e)

    def update(self, vdag_id, update_fields):
        try:
            result = self.collection.update_one(
                {"vdagURI": vdag_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Document with vdagURI {vdag_id} updated")
                return True, result.modified_count
            else:
                logger.info(
                    f"No document found with vdagURI {vdag_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating document: {e}")
            return False, str(e)

    def delete(self, vdag_id):
        try:
            result = self.collection.delete_one({"vdagURI": vdag_id})
            if result.deleted_count > 0:
                logger.info(f"Document with vdagURI {vdag_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(
                    f"No document found with vdagURI {vdag_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting document: {e}")
            return False, str(e)

    def query(self, query_filter):
        try:
            result = self.collection.find(query_filter)
            documents = list(result)
            logger.info(f"Query successful, found {len(documents)} documents")
            processed_results = []
            for r in documents:
                del r['_id']
                processed_results.append(r)
            return True, processed_results
        except errors.PyMongoError as e:
            logger.error(f"Error querying documents: {e}")
            return False, str(e)
    
    def aggregate(self, pipeline):
        try:
            result = self.collection.aggregate(pipeline)
            documents = list(result)
            logger.info(f"Aggregation successful, returned {len(documents)} documents")

            for doc in documents:
                doc.pop("_id", None)

            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error running aggregation: {e}")
            return False, str(e)


class VDAGMetricsListener:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = 6379
        self.redis_queue = "vDAG_METRICS"
        self.mongo_uri = os.getenv("MONGO_URL")
        self.mongo_db = "vdag_metrics"
        self.redis_conn = None
        self.mongo_conn = None
        self.vdag_metrics = None

    def connect_to_redis(self, max_retries=100, base_delay=3):
        retry_count = 0
        while retry_count < max_retries:
            try:
                self.redis_conn = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                )

                self.redis_conn.ping()
                logger.info("Connected to Redis")
                return True
            except Exception as e:
                logger.warning(f"Redis connection attempt {retry_count + 1} failed: {e}")
                retry_count += 1
                time.sleep(base_delay * retry_count)
        logger.error("Max Redis connection attempts exceeded. Giving up.")
        self.redis_conn = None
        return False

    def connect_to_mongo(self):
        try:
            self.mongo_conn = MongoClient(self.mongo_uri)
            db = self.mongo_conn[self.mongo_db]
            self.vdag_metrics = db["vdag_metrics"]
            logger.info("Connected to MongoDB")
        except errors.ConnectionFailure as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            self.mongo_conn = None

    def upsert_vdag_metrics(self, metrics):
        try:

            logger.info(f"received metrics: {metrics}")
            vdag_id = metrics.get("vdagControllerId")
            result = self.vdag_metrics.update_one(
                    {"vdagControllerId": vdag_id},
                    {"$set": metrics},
                    upsert=True
            )
            if result.upserted_id:
                logger.info(f"Upserted new document with ID: {result.upserted_id}")
            else:
                logger.info(f"Updated document with vdagURI: {vdag_id}")
        except errors.PyMongoError as e:
            logger.error(f"Error upserting document: {e}")

    def listen_for_metrics(self):
        self.connect_to_mongo()
        self.connect_to_redis()

        while True:
            if not self.redis_conn and not self.connect_to_redis():
                logger.error("Redis connection not available, retrying in 5 seconds")
                time.sleep(5)
                continue

            try:
                _, message = self.redis_conn.brpop(self.redis_queue)
                if message:
                    metrics = json.loads(message)
                    self.upsert_vdag_metrics(metrics)
            except Exception as e:
                logger.warning(f"Lost Redis connection: {e}")
                self.redis_conn = None
                time.sleep(5)

    def start_listener(self):
        listener_thread = threading.Thread(target=self.listen_for_metrics)
        listener_thread.daemon = True
        listener_thread.start()
        logger.info("vDAG metrics listener thread started")

