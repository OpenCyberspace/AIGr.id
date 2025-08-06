import redis
import json
import logging
import time
from threading import Thread
from typing import Dict

from .jobs_db import PolicyJobs, PolicyJobsDB


class OutputListener:
    def __init__(self, redis_host="localhost", redis_port=6379, redis_queue="JOB_OUTPUTS", max_retries=10):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_queue = redis_queue
        self.max_retries = max_retries
        self.db = PolicyJobsDB()

        logging.basicConfig(level=logging.INFO)
        self._connect_to_redis()

    def _connect_to_redis(self):
        retries = 0
        while retries < self.max_retries:
            try:
                self.redis_client = redis.StrictRedis(
                    host=self.redis_host, port=self.redis_port, decode_responses=True
                )
                # Test the connection
                self.redis_client.ping()
                logging.info("Connected to Redis.")
                return
            except Exception as e:
                retries += 1
                wait = min(2 ** retries, 30)
                logging.warning(f"Redis connection failed (attempt {retries}): {e}. Retrying in {wait} seconds...")
                time.sleep(wait)

        raise RuntimeError("Failed to connect to Redis after multiple retries.")

    def _process_message(self, message: Dict):
        try:
            job_id = message.get("job_id")
            job_output_data = message.get("job_output_data")
            job_status = message.get("job_status")
            node_id = message.get("node_id")
            job_policy_rule_uri = message.get("job_policy_rule_uri")

            existing_job = self.db.read(job_id)
            if existing_job:
                existing_job.job_output_data = job_output_data
                existing_job.job_status = job_status
                existing_job.node_id = node_id
                existing_job.job_policy_rule_uri = job_policy_rule_uri
                updated = self.db.update(job_id, existing_job)
                logging.info(f"Job '{job_id}' updated: {updated}")
            else:
                new_job = PolicyJobs(
                    job_id=job_id,
                    job_output_data=job_output_data,
                    job_status=job_status,
                    node_id=node_id,
                    job_policy_rule_uri=job_policy_rule_uri
                )
                created = self.db.create(new_job)
                logging.info(f"Job '{job_id}' created: {created}")

        except Exception as e:
            logging.error(f"Error processing message: {e}")

    def listen(self):
        logging.info("Listening for job outputs...")
        while True:
            try:
                message = self.redis_client.blpop(self.redis_queue)
                if message:
                    queue_name, job_output = message
                    try:
                        job_data = json.loads(job_output)
                        self._process_message(job_data)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to decode message: {job_output}, error: {e}")
            except redis.exceptions.ConnectionError as e:
                logging.error(f"Redis connection error during listen: {e}")
                self._connect_to_redis()
            except Exception as e:
                logging.error(f"Unexpected error in listener: {e}")
                time.sleep(5)

    def start(self):
        listener_thread = Thread(target=self.listen, daemon=True)
        listener_thread.start()
        logging.info("OutputListener thread started.")


def start_output_listener(redis_host="localhost", redis_port=6379, redis_queue="JOB_OUTPUTS"):
    try:
        listener = OutputListener(redis_host=redis_host, redis_port=redis_port, redis_queue=redis_queue)
        listener.start()
        logging.info("OutputListener started in the background.")
        return listener
    except Exception as e:
        logging.error(f"Failed to start OutputListener: {e}")
        raise
