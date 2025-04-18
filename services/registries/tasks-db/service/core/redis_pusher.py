import json
import logging
import time
import redis

logger = logging.getLogger(__name__)


class UpdatesRedisPusher:
    def __init__(self):
        self.redis_client = None
        self._connect_to_redis()

    def _connect_to_redis(self):
        while self.redis_client is None:
            try:
                self.redis_client = redis.StrictRedis(
                    host='localhost', port=6379, db=0, decode_responses=True)
                self.redis_client.ping()
                logger.info("Connected to Redis successfully")
            except redis.ConnectionError as e:
                logger.error(
                    f"Redis connection failed: {e}, retrying in 5 seconds...")
                time.sleep(5)
                self.redis_client = None

    def push_update(self, task_id: str, status: str, task_status_data: dict):
        if not self.redis_client:
            self._connect_to_redis()

        try:
            update_data = {
                "task_id": task_id,
                "status": status,
                "task_status_data": task_status_data
            }
            self.redis_client.lpush("TASK_UPDATES", json.dumps(update_data))
            logger.info(
                f"Pushed update for task_id {task_id} to TASK_UPDATES queue")
        except redis.RedisError as e:
            logger.error(f"Error pushing update to Redis: {e}")
            self.redis_client = None 
