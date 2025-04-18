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


def get_pod_ips(block_id):

    pods = scan_pods_in_namespace("blocks", block_id)
    pod_ips = [pod.status.pod_ip for pod in pods if pod.status.pod_ip]

    return pod_ips

