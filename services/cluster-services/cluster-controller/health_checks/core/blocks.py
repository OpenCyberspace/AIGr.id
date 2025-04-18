import logging
import requests
import threading
import json
import redis
from kubernetes import client, config
import os

from .callback import PolicyEvaluator

logging.basicConfig(level=logging.INFO)


class FailurePolicyClient:
    def __init__(self, api_url):
        self.api_url = api_url

    def execute_failure_policy(self, failure_policy_id, inputs, parameters):
        payload = {
            "failure_policy_id": failure_policy_id,
            "inputs": inputs,
            "parameters": parameters
        }
        try:
            logging.info(
                f"Sending request to {self.api_url}/executeFailurePolicy with payload: {payload}")
            response = requests.post(
                f"{self.api_url}/executeFailurePolicy", json=payload)
            if response.status_code == 200:
                data = response.json()['data']
                return data
            else:
                raise Exception(response['message'])

        except requests.RequestException as e:
            logging.error(f"API request failed: {e}")
            return {"success": False, "message": str(e)}


class Blocks:
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        self.registered_health_checkers = {}
        self.redis_client = redis.Redis(
            host=redis_host, port=redis_port, db=redis_db)
        self.key_prefix = 'health_checker__'
        self.threads = {}
        config.load_kube_config()
        logging.info("Blocks initialized")

        self.load_health_checkers_from_redis()
        self.failure_policy_client = FailurePolicyClient(
            os.getenv("FAILURE_HANDLER_SERVER", "http://localhost:7000")
        )

        self.local_evaluators = {}

    def register_health_checker(self, checker_id, checker_data):
        try:
            self.registered_health_checkers[checker_id] = checker_data
            redis_key = self.key_prefix + checker_id
            self.redis_client.set(redis_key, json.dumps(checker_data))
            self.start_health_check_thread(checker_id, checker_data)
            logging.info(f"Health checker {checker_id} registered")
        except Exception as e:
            logging.error(
                f"Error registering health checker {checker_id}: {str(e)}")
            raise

    def unregister_health_checker(self, checker_id):
        try:
            if checker_id in self.registered_health_checkers:
                del self.registered_health_checkers[checker_id]
                redis_key = self.key_prefix + checker_id
                self.redis_client.delete(redis_key)
                self.stop_health_check_thread(checker_id)
                logging.info(f"Health checker {checker_id} unregistered")
        except Exception as e:
            logging.error(
                f"Error unregistering health checker {checker_id}: {str(e)}")
            raise

    def load_health_checkers_from_redis(self):
        try:
            keys = self.redis_client.keys(self.key_prefix + '*')
            for key in keys:
                checker_id = key.decode('utf-8').replace(self.key_prefix, '')
                checker_data = json.loads(self.redis_client.get(key))
                self.register_health_checker(checker_id, checker_data)
            logging.info("Health checkers loaded from Redis")
            return self.registered_health_checkers
        except Exception as e:
            logging.error(
                f"Error loading health checkers from Redis: {str(e)}")
            raise

    def mgmt(self, block_id, action, data):
        try:

            if block_id not in self.local_evaluators:
                raise Exception(
                    f"evaluator for block_id {block_id} is not registered")

            policy_executor: PolicyEvaluator = self.local_evaluators[block_id]
            return policy_executor.mgmt(action, data)

        except Exception as e:
            raise e

    def start_health_check_thread(self, checker_id, checker_data):
        try:
            if checker_id not in self.threads:
                thread = threading.Thread(
                    target=self.health_check_worker, args=(checker_id, checker_data))
                thread.daemon = True
                self.threads[checker_id] = {
                    'thread': thread,
                    'stop_event': threading.Event()
                }
                thread.start()
                logging.info(f"Health check thread started for {checker_id}")
        except Exception as e:
            logging.error(
                f"Error starting health check thread for {checker_id}: {str(e)}")
            raise

    def stop_health_check_thread(self, checker_id):
        try:
            if checker_id in self.threads:
                self.threads[checker_id]['stop_event'].set()
                self.threads[checker_id]['thread'].join()
                del self.threads[checker_id]
                logging.info(f"Health check thread stopped for {checker_id}")
        except Exception as e:
            logging.error(
                f"Error stopping health check thread for {checker_id}: {str(e)}")
            raise

    def health_check_worker(self, checker_id, checker_data):
        try:
            namespace = "blocks"
            block_id = checker_id
            interval = checker_data['settings'].get('interval', 60)
            max_times = checker_data['settings'].get('max_times', 3)
            timeout_interval = checker_data['settings'].get(
                'timeout_interval', 5)

            policy_rule_uri = checker_data.get('policy_rule_uri')
            settings = checker_data.get('settings', {})

            settings.update({
                "failure_policy_caller": self.failure_policy_client.execute_failure_policy
            })

            policy_evaluator = PolicyEvaluator(
                policy_rule_uri, settings, block_id
            )

            self.local_evaluators[block_id] = policy_evaluator

            v1 = client.CoreV1Api()
            stop_event = self.threads[checker_id]['stop_event']

            # Dictionary to store failure counts for each instanceID
            instance_failure_counts = {}

            while not stop_event.is_set():
                try:
                    pods = v1.list_namespaced_pod(
                        namespace, label_selector=f"blockID={block_id}")
                    print(
                        f'pods found for blockID={block_id}', len(pods.items))
                    if not pods.items:
                        # No pods found
                        for instance_id in instance_failure_counts:
                            if instance_failure_counts[instance_id] > max_times:
                                logging.error(
                                    f"block instance {instance_id} not active")
                                policy_evaluator.execute_rule(instance_id)
                    else:
                        for pod in pods.items:
                            pod_ip = pod.status.pod_ip
                            instance_id = pod.metadata.labels.get('instanceID')
                            if not instance_id:
                                continue  # Skip pods without instanceID label

                            if instance_id not in instance_failure_counts:
                                instance_failure_counts[instance_id] = 0

                            try:
                                response = requests.get(
                                    f"http://{pod_ip}:18000s/health", timeout=timeout_interval)
                                if response.status_code == 200:
                                    # Reset failure count on success
                                    instance_failure_counts[instance_id] = 0
                                else:
                                    instance_failure_counts[instance_id] += 1
                                    if instance_failure_counts[instance_id] > max_times:
                                        logging.error(
                                            f"block instance {instance_id} not active")
                                        policy_evaluator.execute_rule(
                                            instance_id)
                            except requests.RequestException as e:
                                logging.error(
                                    f"Health check failed for pod {pod.metadata.name} at {pod_ip}: {e}")
                                instance_failure_counts[instance_id] += 1
                                if instance_failure_counts[instance_id] > max_times:
                                    logging.error(
                                        f"block instance {instance_id} not active")
                                    policy_evaluator.execute_rule(instance_id)

                except Exception as e:
                    logging.error(f"Error fetching pods: {e}")

                stop_event.wait(interval)

        except Exception as e:
            logging.error(
                f"Unexpected error in health check worker for {checker_id}: {str(e)}")
            raise
