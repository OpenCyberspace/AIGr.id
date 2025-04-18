import redis
import json
import logging
from threading import Thread
from typing import Dict

from .jobs_db import PolicyJobs, PolicyJobsDB


class OutputListener:
    def __init__(self, redis_host="localhost", redis_port=6379, redis_queue="JOB_OUTPUTS"):
        try:
            self.redis_client = redis.StrictRedis(
                host=redis_host, port=redis_port, decode_responses=True)
            self.redis_queue = redis_queue
            self.db = PolicyJobsDB()
            logging.basicConfig(level=logging.INFO)
        except Exception as e:
            logging.error(f"Failed to initialize OutputListener: {e}")
            raise RuntimeError(f"Failed to initialize OutputListener: {e}")

    def _process_message(self, message: Dict):
        try:
            job_id = message.get("job_id")
            job_output_data = message.get("job_output_data")
            job_status = message.get("job_status")
            node_id = message.get("node_id")
            job_policy_rule_uri = message.get("job_policy_rule_uri")

            if not all([job_id, job_output_data, job_status, node_id, job_policy_rule_uri]):
                logging.warning(f"Invalid message received: {message}")
                return

            existing_job = self.db.read(job_id)
            if existing_job:
                # Update existing job
                existing_job.job_output_data = job_output_data
                existing_job.job_status = job_status
                existing_job.node_id = node_id
                existing_job.job_policy_rule_uri = job_policy_rule_uri
                updated = self.db.update(job_id, existing_job)
                logging.info(f"Job '{job_id}' updated: {updated}")
            else:
                # Create new job entry
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
        try:
            logging.info("Listening for job outputs...")
            while True:
                message = self.redis_client.blpop(self.redis_queue)
                if message:
                    queue_name, job_output = message
                    try:
                        job_data = json.loads(job_output)
                        self._process_message(job_data)
                    except json.JSONDecodeError as e:
                        logging.error(
                            f"Failed to decode message: {job_output}, error: {e}")
        except Exception as e:
            logging.error(f"Error in listener: {e}")

    def start(self):
        listener_thread = Thread(target=self.listen, daemon=True)
        listener_thread.start()
        logging.info("OutputListener thread started.")


def start_output_listener(redis_host="localhost", redis_port=6379, redis_queue="JOB_OUTPUTS"):

    try:
        listener = OutputListener(
            redis_host=redis_host, redis_port=redis_port, redis_queue=redis_queue)
        listener_thread = Thread(target=listener.listen, daemon=True)
        listener_thread.start()
        logging.info("OutputListener started in the background.")
        return listener
    except Exception as e:
        logging.error(f"Failed to start OutputListener: {e}")
        raise
