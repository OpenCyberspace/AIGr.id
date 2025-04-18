import os
import json
import redis
import logging
from urllib.parse import urlparse

class BlockEvents:
    def __init__(self, queue_name='EVENTS_QUEUE'):
        self.queue_name = queue_name
        self.redis_url = os.getenv("BLOCK_EVENTS_REDIS_URL", "redis://localhost:6379")
        self.block_id = os.getenv("BLOCK_ID", "UNKNOWN_BLOCK")
        self.redis_client = None

    def connect_to_redis(self):
        try:
            parsed_url = urlparse(self.redis_url)
            host = parsed_url.hostname
            port = parsed_url.port
            client = redis.StrictRedis(
                host=host,
                port=port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            logging.info(f"Connected to Redis for BlockEvents at {host}:{port}")
            return client
        except Exception as e:
            logging.error(f"Redis connection error: {e}")
            raise

    def get_client(self):
        if self.redis_client:
            return self.redis_client
        self.redis_client = self.connect_to_redis()
        return self.redis_client

    def push_event(self, event_name, event_data):
        event_payload = {
            "event_name": event_name,
            "block_id": self.block_id,
            "event_data": event_data
        }
        event_json = json.dumps(event_payload)

        client = self.get_client()
        for attempt in range(2):  # try original client, then reconnect once
            try:
                client.rpush(self.queue_name, event_json)
                logging.info(f"Event '{event_name}' pushed to queue for block {self.block_id}")
                return
            except redis.exceptions.RedisError as e:
                logging.warning(f"Push failed on attempt {attempt + 1}: {e}")
                if attempt == 0:
                    self.redis_client = self.connect_to_redis()
                    client = self.redis_client
                else:
                    logging.error(f"Failed to push event after reconnecting: {e}")
                    raise

