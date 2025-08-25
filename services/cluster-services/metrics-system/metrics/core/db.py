from pymongo import MongoClient, errors
import logging
import os
import time
import redis
import threading
import json
import bson.json_util

from .writers import ClusterMetricsWriter, BlockMetricsWriter, vDAGMetricsWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def aggregate_metrics(metrics):

    def aggregate_inner(node_metrics_list):
        aggregated_metrics = {}

        def add_to_aggregate(key, value, operation='sum'):
            if key not in aggregated_metrics:
                if operation == 'average':
                    # Use a list for averaging
                    aggregated_metrics[key] = [value]
                else:
                    aggregated_metrics[key] = value
            else:
                if operation == 'sum':
                    aggregated_metrics[key] += value
                elif operation == 'average':
                    aggregated_metrics[key].append(value)
                elif operation == 'max':
                    aggregated_metrics[key] = max(
                        aggregated_metrics[key], value)
                elif operation == 'min':
                    aggregated_metrics[key] = min(
                        aggregated_metrics[key], value)

        def process_metrics(metrics_dict, parent_key=""):
            if isinstance(metrics_dict, list):
                # If it's a list, recursively process each item with an index key or just skip
                for i, item in enumerate(metrics_dict):
                    process_metrics(item, parent_key=f"{parent_key}[{i}]")
                return

            for key, value in metrics_dict.items():
                full_key = f"{parent_key}.{key}" if parent_key else key
                if isinstance(value, dict):
                    process_metrics(value, parent_key=full_key)
                elif isinstance(value, list):
                    # Optionally flatten list of dicts or skip
                    for i, item in enumerate(value):
                        process_metrics(item, parent_key=f"{full_key}[{i}]")
                elif isinstance(value, str):
                    continue
                else:
                    if 'averageUtil' in full_key or 'load1m' in full_key or 'load5m' in full_key or 'load15m' in full_key:
                        add_to_aggregate(full_key, value, operation='average')
                    elif 'maxDisk' in full_key:
                        add_to_aggregate(full_key, value, operation='max')
                    elif 'minDisk' in full_key:
                        add_to_aggregate(full_key, value, operation='min')
                    else:
                        add_to_aggregate(full_key, value, operation='sum')


        for node_metrics in node_metrics_list:
            process_metrics(node_metrics)

        # Compute average for average utilization and load metrics
        for key in aggregated_metrics:
            # Only average if it's a list
            if isinstance(aggregated_metrics[key], list):
                aggregated_metrics[key] = sum(
                    aggregated_metrics[key]) / len(aggregated_metrics[key])

        return aggregated_metrics

    if len(metrics) == 0:
        return {}

    all_aggregated = {}

    ref = metrics[0]
    for key in ref:

        if key == "id":
            continue

        values = []

        for m in metrics:
            if key in m:
                values.append(m[key])
            else:
                continue

        logger.info(f"sending values for aggregated = {values}")
        all_aggregated[key] = aggregate_inner(values)

    return all_aggregated


class NodeMetrics:
    def __init__(self):
        try:

            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
            self.client = MongoClient(uri)
            self.db = self.client["metrics"]
            self.collection = self.db['node_metrics']
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

    def update(self, node_id, update_fields):
        try:
            result = self.collection.update_one(
                {"nodeId": node_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Document with nodeId {node_id} updated")
                return True, result.modified_count
            else:
                logger.info(
                    f"No document found with nodeId {node_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating document: {e}")
            return False, str(e)

    def delete(self, node_id):
        try:
            result = self.collection.delete_one({"nodeId": node_id})
            if result.deleted_count > 0:
                logger.info(f"Document with nodeId {node_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(
                    f"No document found with nodeId {node_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting document: {e}")
            return False, str(e)

    def query(self, query_filter):
        try:

            logger.info(f"executing query {query_filter}")
            result = self.collection.find(query_filter)
            documents = list(result)

            documents_updated = []
            for doc in documents:
                if '_id' in doc:
                    del doc['_id']
                    documents_updated.append(doc)

            logger.info(f"Query successful, found {len(documents_updated)} documents")
            return True, documents_updated
        except errors.PyMongoError as e:
            logger.error(f"Error querying documents: {e}")
            return False, str(e)


class BlockMetrics:
    def __init__(self):
        try:

            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
            self.client = MongoClient(uri)
            self.db = self.client["metrics"]
            self.collection = self.db['app_metrics']
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

    def update(self, block_id, update_fields):
        try:
            result = self.collection.update_one(
                {"blockId": block_id},
                {"$set": update_fields}
            )
            if result.modified_count > 0:
                logger.info(f"Document with nodeId {block_id} updated")
                return True, result.modified_count
            else:
                logger.info(
                    f"No document found with nodeId {block_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating document: {e}")
            return False, str(e)

    def delete(self, block_id):
        try:
            result = self.collection.delete_one({"blockId": block_id})
            if result.deleted_count > 0:
                logger.info(f"Document with nodeId {block_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(
                    f"No document found with nodeId {block_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting document: {e}")
            return False, str(e)

    def query(self, query_filter):
        try:
            result = self.collection.find(query_filter)
            documents = list(result)

            documents_updated = []
            for doc in documents:
                if '_id' in doc:
                    del doc['_id']
                    documents_updated.append(doc)

            logger.info(
                f"Query successful, found {len(documents_updated)} documents")
            return True, documents_updated
        except errors.PyMongoError as e:
            logger.error(f"Error querying documents: {e}")
            return False, str(e)

    def get_all_metrics(self, block_id):
        try:
            result = self.collection.find({"blockId": block_id})
            documents = list(result)

            documents_updated = []
            for doc in documents:
                if '_id' in doc:
                    del doc['_id']
                    documents_updated.append(doc)

            return True, documents_updated
        except Exception as e:
            raise e


class Cluster:
    def __init__(self):
        self.node_metrics = NodeMetrics()

    def get_metrics(self, query):
        success, result = self.node_metrics.query(query)
        if success:
            logger.info("Successfully retrieved all node metrics")
            return True, result
        else:
            logger.error(f"Failed to retrieve node metrics: {result}")
            return False, result

    def get_all_metrics(self, cluster_id):
        success, result = self.get_metrics({"clusterId": cluster_id})
        if not success:
            logger.error(f"Failed to retrieve node metrics: {result}")
            return False, result

        result = [r.get('metrics', {}).get('resource', {}).get('node')
                  for r in result]

        logging.info(f"metrics data: {result}")

        aggregated = aggregate_metrics(result)

        return True, {
            "cluster_metrics": aggregated,
            "node_metrics": result
        }


class MetricsListener:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_queue = "NODE_METRICS"
        self.mongo_uri = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
        self.mongo_db = "metrics"
        self.redis_conn = None
        self.mongo_conn = None
        self.node_metrics = None
        self.cluster_id = os.getenv("CLUSTER_ID", "cluster-123")

        self.block_metrics_writer = BlockMetricsWriter(
            redis_host=os.getenv("BLOCK_METRICS_GLOBAL_DB_REDIS_HOST", "localhost")
        )

        self.vdag_metrics_writer = vDAGMetricsWriter(
            redis_host=os.getenv("VDAG_METRICS_GLOBAL_DB_REDIS_HOST", "localhost")
        )

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
            self.node_metrics = db['node_metrics']
            self.app_metrics = db['app_metrics']
            logger.info("Connected to MongoDB")
        except errors.ConnectionFailure as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            self.mongo_conn = None

    def upsert_metrics_hardware(self, metrics):
        try:
            node_id = metrics.get("nodeId")
            if node_id:
                result = self.node_metrics.update_one(
                    {"nodeId": node_id},
                    {"$set": metrics},
                    upsert=True
                )
                if result.upserted_id:
                    logger.info(
                        f"Upserted new document with ID: {result.upserted_id}")
                else:
                    logger.info(f"Updated document with nodeId: {node_id}")
        except errors.PyMongoError as e:
            logger.error(f"Error upserting document: {e}")

    def upsert_metrics_app(self, metrics):
        try:
            instance_id = metrics.get("instanceId")
            block_id = metrics.get("blockId")

            if instance_id == "executor":

                all_block_metrics = list(self.app_metrics.find({"blockId": block_id}))

                processed = []

                for m in all_block_metrics:
                    if '_id' in m:
                        del m['_id']
                        processed.append(m)

                logger.info("writing all block metrics: {}".format(processed))

                metrics_data = {
                    "blockId": block_id,
                    "instances": processed
                }

                self.block_metrics_writer.write(metrics_data)

            if instance_id:
                result = self.app_metrics.update_one(
                    {"nodeKey": instance_id + "__" + block_id},
                    {"$set": metrics},
                    upsert=True
                )
                if result.upserted_id:
                    logger.info(
                        f"Upserted new document with ID: {result.upserted_id}")
                else:
                    logger.info(
                        f"Updated document with nodeId: {instance_id +  block_id}")
        except errors.PyMongoError as e:
            logger.error(f"Error upserting document: {e}")

    def upsert_vdag_metrics(self, metrics):
        try:
            self.vdag_metrics_writer.write(metrics)
        except Exception as e:
            raise e

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

                        if metrics['type'] == "app":
                            self.upsert_metrics_app(metrics)
                        elif metrics['type'] == "vdag":
                            self.upsert_vdag_metrics(metrics)
                        else:
                            self.upsert_metrics_hardware(metrics)
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
        logger.info("Metrics listener thread started")


class ClusterMetricsWriterThread:
    def __init__(self, interval=None):
        try:
            self.writer = ClusterMetricsWriter(
                redis_host=os.getenv("CLUSTER_METRICS_GLOBAL_DB_REDIS_HOST")
            )

            self.interval = interval or int(
                os.getenv("CLUSTER_METRICS_WRITE_INTERVAL", 30))
            if self.interval <= 0:
                raise ValueError("Interval must be a positive integer.")
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.db = Cluster()
            self.stop_event = threading.Event()
            self.cluster_id = os.getenv("CLUSTER_ID", "cluster-123")
            logger.info(
                f"ClusterMetricsWriterThread initialized with interval {self.interval}s")
        except Exception as e:
            logger.error(f"Error initializing ClusterMetricsWriterThread: {e}")
            raise

    def start(self):
        try:
            self.stop_event.clear()
            self.thread.start()
            logger.info("ClusterMetricsWriterThread started")
        except Exception as e:
            logger.error(f"Error starting ClusterMetricsWriterThread: {e}")
            raise

    def stop(self):
        try:
            self.stop_event.set()
            self.thread.join()
            logger.info("ClusterMetricsWriterThread stopped")
        except Exception as e:
            logger.error(f"Error stopping ClusterMetricsWriterThread: {e}")

    def _run(self):
        while not self.stop_event.is_set():
            try:

                # get aggregated metrics:
                ret, metrics = self.db.get_all_metrics(self.cluster_id)
                if not ret:
                    raise Exception(str(metrics))

                data = {
                    "clusterId": self.cluster_id,
                    "cluster": metrics['cluster_metrics'],
                    "nodes": metrics['node_metrics']
                }

                self.writer.write(data)

                logger.info("ClusterMetricsWriter write() called")
            except Exception as e:
                logger.error(f"Error in ClusterMetricsWriterThread loop: {e}")
            time.sleep(self.interval)

class BlockMetricsDeleteThread:
    def __init__(self, interval=None):
        try:
            self.mongo_uri = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
            self.mongo_db = os.getenv("MONGO_DB", "metrics")
            self.mongo_conn = MongoClient(self.mongo_uri)
            db = self.mongo_conn[self.mongo_db]
            self.node_metrics = db['node_metrics']
            self.app_metrics = db['app_metrics']
            self.interval = interval or int(os.getenv("BLOCK_METRICS_DELETE_INTERVAL", 180))
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.stop_event = threading.Event()
            logger.info("BlockMetricsDeleteThread connected to MongoDB")
        except errors.ConnectionFailure as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            self.mongo_conn = None
        except Exception as e:
            logger.error(f"Error initializing BlockMetricsDeleteThread: {e}")
            raise

    def start(self):
        try:
            self.stop_event.clear()
            self.thread.start()
            logger.info("BlockMetricsDeleteThread started")
        except Exception as e:
            logger.error(f"Error starting BlockMetricsDeleteThread: {e}")
            raise

    def stop(self):
        try:
            self.stop_event.set()
            self.thread.join()
            logger.info("BlockMetricsDeleteThread stopped")
        except Exception as e:
            logger.error(f"Error stopping BlockMetricsDeleteThread: {e}")

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.app_metrics.delete_many({})
                logger.info("BlockMetricsDeleteThread delete() called")
            except Exception as e:
                logger.error(f"Error in BlockMetricsDeleteThread loop: {e}")
            time.sleep(1800)

