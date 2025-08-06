import threading
import logging
import redis
import json
import time
import os
from queue import Queue


from .schema import vDAGObject

logger = logging.getLogger(__name__)


class vDAGInputsListener:
    def __init__(self, internal_queue: Queue):
        self.redis_host = os.getenv("REDIS_HOST_URL", 'redis://localhost:6379/0')
        self.redis_client = None
        self.internal_queue = internal_queue
        self.queue_name = "INPUTS"
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)

    def start(self):
        logger.info("Starting vDAGInputsListener...")
        self._connect_redis()
        self.listener_thread.start()

    def _connect_redis(self):
        while True:
            try:
                self.redis_client = redis.StrictRedis.from_url(self.redis_host)
                self.redis_client.ping()
                logger.info("Connected to Redis successfully.")
                break
            except redis.ConnectionError as e:
                logger.error(
                    f"Redis connection error: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def _listen(self):
        while True:
            try:
                _, message = self.redis_client.brpop(self.queue_name)
                logger.info("Received message from Redis queue")
                data = json.loads(message)

                task_id = data['task_id']
                task_data = data['task_data']

                vdag_object = vDAGObject.from_dict(task_data)
                self.internal_queue.put((task_id, vdag_object))
                logger.info(
                    f"vDAGObject pushed to internal queue: {vdag_object.vdagURI}")
            except Exception as e:
                logger.error(f"Unexpected error in vDAGInputsListener: {e}")
                self._connect_redis()
