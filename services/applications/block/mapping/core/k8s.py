from kubernetes import client, config
import requests
import threading
import time
import redis
import json
import os

import logging

logging.basicConfig(level=logging.INFO)


def scan_pods_in_namespace(namespace, block_id):
    try:
        config.load_incluster_config()
    except Exception as e:
        config.load_kube_config()
        
    v1 = client.CoreV1Api()
    pods_with_blockid = []

    try:
        label_selector = f"blockID={block_id}"
        pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)
        for pod in pods.items:
            pods_with_blockid.append(pod)
    except client.exceptions.ApiException as e:
        print(f"Exception when calling CoreV1Api->list_namespaced_pod: {e}")

    return pods_with_blockid


class UpdateNotifier:
    def __init__(self, redis_host, redis_port, redis_password):
        self.redis_client = redis.StrictRedis(
            host=redis_host, port=redis_port, password=redis_password, decode_responses=True)
        try:
            config.load_incluster_config()
        except Exception as e:
            config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.current_pods = []

    def scan_pods_in_namespace(self, namespace, block_id):
        pods_with_blockid = []
        try:
            label_selector = f"blockID={block_id}"
            pods = self.v1.list_namespaced_pod(
                namespace, label_selector=label_selector)
            pods_with_blockid = pods.items
        except client.exceptions.ApiException as e:
            print(
                f"Exception when calling CoreV1Api->list_namespaced_pod: {e}")
        return pods_with_blockid

    def _get_ids_list(self, pods):
        instance_ids = [pod.metadata.labels.get("instanceID") for pod in pods]
        return instance_ids

    def listen_for_changes(self, namespace, block_id):
        while True:
            new_pods = self.scan_pods_in_namespace(namespace, block_id)
            if len(new_pods) != len(self.current_pods):
                logging.info(f"pushing instance updates: old_length={len(self.current_pods)}, new_length={len(new_pods)}")
                serialized_pods = { "instances": [pod.to_dict() for pod in new_pods], "ids": self._get_ids_list(new_pods) }
                self.redis_client.lpush(
                    "K8s_POD_LIST_EXECUTOR", json.dumps(serialized_pods, default=str))
                self.redis_client.lpush(
                    "K8s_POD_LIST_AUTOSCALER", json.dumps(serialized_pods, default=str))
                self.current_pods = new_pods
            time.sleep(10)

    def start_listening_thread(self, namespace, block_id):
        self.thread = threading.Thread(
            target=self.listen_for_changes, args=(namespace, block_id))
        self.thread.start()

    def stop_listening_thread(self):
        self.thread_stop_event.set()
        if self.thread:
            self.thread.join()


def query_all_metrics(prometheus_url, instance_id):
    try:
        response = requests.get(
            f"{prometheus_url}/api/v1/label/__name__/values")
        response.raise_for_status()
        metric_names = response.json().get('data', [])

        metrics = []
        for metric_name in metric_names:
            query = f"{metric_name}{{instance='{instance_id}'}}"
            metric_response = requests.get(
                f"{prometheus_url}/api/v1/query", params={'query': query})
            metric_response.raise_for_status()
            result = metric_response.json().get('data', {}).get('result', [])

            for item in result:
                metrics.append(
                    {'name': metric_name, 'value': item['value'][1]})

        return metrics
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def start_update_notifier():
    namespace = "blocks"
    block_id = os.getenv("BLOCK_ID")

    notifier = UpdateNotifier('localhost', 6379, redis_password=None)
    notifier.start_listening_thread(namespace, block_id)
    logging.info("started update notifier")


def query_metrics(namespace, block_id, prometheus_url):
    pods = scan_pods_in_namespace(namespace, block_id)
    results = []

    for pod in pods:
        instance_id = pod.metadata.labels.get("instanceID")
        if instance_id:
            metrics = query_all_metrics(prometheus_url, instance_id)
            results.append({'instanceID': instance_id, 'metrics': metrics})

    return results
