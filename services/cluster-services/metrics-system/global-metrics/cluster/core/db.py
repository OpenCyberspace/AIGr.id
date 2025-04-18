import redis
import threading
import json
import time
import os
from pymongo import MongoClient, errors
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ClusterMetrics:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["cluster_metrics"]
            self.collection = self.db["cluster_metrics"]
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

    def update(self, cluster_id, update_fields):
        try:
            result = self.collection.update_one(
                {"clusterId": cluster_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Document with clusterId {cluster_id} updated")
                return True, result.modified_count
            else:
                logger.info(
                    f"No document found with clusterId {cluster_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating document: {e}")
            return False, str(e)

    def delete(self, cluster_id):
        try:
            result = self.collection.delete_one({"clusterId": cluster_id})
            if result.deleted_count > 0:
                logger.info(f"Document with clusterId {cluster_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(
                    f"No document found with clusterId {cluster_id} to delete")
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


class ClusterMetricsListener:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_queue = "CLUSTER_METRICS"
        self.mongo_uri = os.getenv("MONGO_URL")
        self.mongo_db = "cluster_metrics"
        self.redis_conn = None
        self.mongo_conn = None
        self.cluster_metrics = None

    def connect_to_redis(self):
        try:
            self.redis_conn = redis.Redis(
                host=self.redis_host, port=self.redis_port)
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            self.redis_conn = None

    def connect_to_mongo(self):
        try:
            self.mongo_conn = MongoClient(self.mongo_uri)
            db = self.mongo_conn[self.mongo_db]
            self.cluster_metrics = db["cluster_metrics"]
            logger.info("Connected to MongoDB")
        except errors.ConnectionFailure as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            self.mongo_conn = None

    def upsert_cluster_metrics(self, metrics):
        try:
            cluster_id = metrics.get("clusterId")
            if cluster_id:
                result = self.cluster_metrics.update_one(
                    {"clusterId": cluster_id},
                    {"$set": metrics},
                    upsert=True
                )
                if result.upserted_id:
                    logger.info(
                        f"Upserted new document with ID: {result.upserted_id}")
                else:
                    logger.info(
                        f"Updated document with cluster_id: {cluster_id}")
        except errors.PyMongoError as e:
            logger.error(f"Error upserting document: {e}")

    def listen_for_metrics(self):
        self.connect_to_redis()
        self.connect_to_mongo()

        while True:
            try:
                if not self.redis_conn:
                    self.connect_to_redis()

                if self.redis_conn:
                    _, message = self.redis_conn.brpop(self.redis_queue)
                    if message:
                        metrics = json.loads(message)
                        self.upsert_cluster_metrics(metrics)
            except redis.exceptions.RedisError as e:
                logger.error(f"Redis error: {e}")
                self.redis_conn = None
                time.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(5)

    def start_listener(self):
        listener_thread = threading.Thread(target=self.listen_for_metrics)
        listener_thread.daemon = True
        listener_thread.start()
        logger.info("Cluster metrics listener thread started")
