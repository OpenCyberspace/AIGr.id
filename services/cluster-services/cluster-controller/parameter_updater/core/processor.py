from .k8s import get_pod_ips
import requests

import requests


import requests


class ServiceManager:
    def __init__(self):
        self.service_ports = {
            "instances": 18001,
            "executor": 18001,
            "autoscaler": 10000,
            "health": 19001,
            "stability": 5000
        }

    def execute_mgmt_command(self, block_id, service_type, mgmt_action, mgmt_data=None):
        if service_type not in self.service_ports:
            raise ValueError(f"Invalid service type: {service_type}")

        if service_type == "instances":
            return self._execute_instances_mgmt_command(block_id, mgmt_action, mgmt_data)
        else:
            return self._execute_service_mgmt_command(block_id, service_type, mgmt_action, mgmt_data)

    def _execute_instances_mgmt_command(self, block_id, mgmt_action, mgmt_data=None):
        pod_ips = get_pod_ips(block_id) 
        port = self.service_ports["instances"]
        results = {}

        for pod_ip in pod_ips:
            url = f"http://{pod_ip}:{port}/mgmt"
            payload = {
                "mgmt_action": mgmt_action,
                "mgmt_data": mgmt_data or {}
            }

            try:
                response = requests.post(url, json=payload, timeout=5)
                results[pod_ip] = response.json()
            except requests.RequestException as e:
                results[pod_ip] = {"success": False, "message": str(e)}

        return results

    def _execute_service_mgmt_command(self, block_id, service_type, mgmt_action, mgmt_data=None):
        port = self.service_ports[service_type]
        url = f"http://{block_id}-executor-svc.blocks.svc.cluster.local:{port}/mgmt"

        payload = {
            "mgmt_action": mgmt_action,
            "mgmt_data": mgmt_data or {}
        }

        try:
            response = requests.post(url, json=payload, timeout=5)
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "message": str(e)}
