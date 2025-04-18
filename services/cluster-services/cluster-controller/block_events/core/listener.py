import redis
import time
import json
import logging

from .executor import ExecutorsCache


class RedisListener:
    def __init__(self, redis_host='localhost', redis_port=6379, queue_name='EVENTS_QUEUE'):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.queue_name = queue_name
        self.redis_client = self.connect_to_redis()
        self.running = True
        self.executor_cache = ExecutorsCache()

    def connect_to_redis(self):
        attempts = 0
        while attempts < 5:
            try:
                client = redis.StrictRedis(
                    host=self.redis_host, port=self.redis_port, decode_responses=True)
                client.ping()
                logging.info("Connected to Redis successfully.")
                return client
            except redis.ConnectionError as e:
                attempts += 1
                logging.error(
                    f"Redis connection failed (attempt {attempts}), retrying in 2 seconds...")
                time.sleep(2)
        raise redis.ConnectionError(
            "Failed to connect to Redis after multiple attempts.")

    def listen(self):
        while self.running:
            try:
                _, event_data = self.redis_client.blpop(self.queue_name)
                if event_data:
                    self.process_event(event_data)
            except redis.ConnectionError:
                logging.error("Redis connection lost. Reconnecting...")
                self.redis_client = self.connect_to_redis()
            except Exception as e:
                logging.error(f"Error processing event: {e}")

    def process_event(self, event_data):
        try:
            event = json.loads(event_data)
            event_name = event.get("event_name")
            block_id = event.get("block_id")
            event_payload = event.get("event_data")

            if not all([event_name, block_id, event_payload]):
                raise ValueError("Invalid event format received")

            logging.info(
                f"Processing event: {event_name} for block {block_id}")
            self.executor_cache.execute_event(
                block_id, event_name, event_payload)
        except json.JSONDecodeError:
            logging.error("Failed to decode event JSON")
        except Exception as e:
            logging.error(f"Error in processing event: {e}")

    def stop(self):
        self.running = False


def main():
    logging.basicConfig(level=logging.INFO)
    listener = RedisListener()
    try:
        listener.listen()
    except Exception:
        logging.info("Shutting down Redis Listener...")
        listener.stop()
