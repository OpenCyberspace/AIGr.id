import redis
import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ClusterMetricsWriter:
    def __init__(self, redis_host="localhost", redis_port=6379, redis_queue="CLUSTER_METRICS"):
        try:
            self.redis_host = redis_host
            self.redis_port = redis_port
            self.redis_queue = redis_queue
            self.redis_conn = redis.Redis(host=self.redis_host, port=self.redis_port)
            logger.info(f"Connected to Redis on {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise

    def write(self, data):
        try:
            if not isinstance(data, dict):
                raise ValueError("Data must be a dictionary")
            serialized_data = json.dumps(data)
            self.redis_conn.lpush(self.redis_queue, serialized_data)
            logger.info(f"Data written to queue '{self.redis_queue}': {data}")
            return True
        except Exception as e:
            logger.error(f"Error writing data to Redis queue: {e}")
            return False


class vDAGMetricsWriter:
    def __init__(self, redis_host="localhost", redis_port=6379, redis_queue="vDAG_METRICS"):
        try:
            self.redis_host = redis_host
            self.redis_port = redis_port
            self.redis_queue = redis_queue
            self.redis_conn = redis.Redis(host=self.redis_host, port=self.redis_port)
            logger.info(f"Connected to Redis on {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise

    def write(self, data):
        try:
            if not isinstance(data, dict):
                raise ValueError("Data must be a dictionary")
            serialized_data = json.dumps(data)
            self.redis_conn.lpush(self.redis_queue, serialized_data)
            logger.info(f"Data written to queue '{self.redis_queue}': {data}")
            return True
        except Exception as e:
            logger.error(f"Error writing data to Redis queue: {e}")
            return False

class BlockMetricsWriter:
    def __init__(self, redis_host="localhost", redis_port=6379, redis_queue="BLOCK_METRICS"):
        try:
            self.redis_host = redis_host
            self.redis_port = redis_port
            self.redis_queue = redis_queue
            self.redis_conn = redis.Redis(host=self.redis_host, port=self.redis_port)
            logger.info(f"Connected to Redis on {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise

    def write(self, data):
        try:
            if not isinstance(data, dict):
                raise ValueError("Data must be a dictionary")
            serialized_data = json.dumps(data)
            self.redis_conn.lpush(self.redis_queue, serialized_data)
            logger.info(f"Data written to queue '{self.redis_queue}': {data}")
            return True
        except Exception as e:
            logger.error(f"Error writing data to Redis queue: {e}")
            return False
