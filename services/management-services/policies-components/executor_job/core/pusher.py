import redis
import logging
import json

class OutputPusher:
    def __init__(self, redis_host="localhost", redis_port=6379, redis_queue="JOB_OUTPUTS"):
        try:
            self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)
            self.redis_queue = redis_queue
            logging.basicConfig(level=logging.INFO)
        except Exception as e:
            logging.error(f"Failed to initialize OutputPusher: {e}")
            raise RuntimeError(f"Failed to initialize OutputPusher: {e}")

    def push(self, job_id: str, job_output_data: dict, job_status: str, node_id: str, job_policy_rule_uri: str):
        try:
            message = {
                "job_id": job_id,
                "job_output_data": job_output_data,
                "job_status": job_status,
                "node_id": node_id,
                "job_policy_rule_uri": job_policy_rule_uri
            }
            self.redis_client.rpush(self.redis_queue, json.dumps(message))
            logging.info(f"Pushed message to queue '{self.redis_queue}': {message}")
        except Exception as e:
            logging.error(f"Failed to push message to queue '{self.redis_queue}': {e}")
