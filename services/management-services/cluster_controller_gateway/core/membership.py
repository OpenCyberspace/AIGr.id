import requests
import logging

from .cluster_controller import get_cluster_membership_connection_url

logger = logging.getLogger(__name__)

class ClusterMembershipClient:
    def __init__(self, cluster_id: str):
        self.cluster_id = cluster_id
        self.base_url = get_cluster_membership_connection_url(self.cluster_id)

    def pre_check_add_node(self, node_data: dict) -> dict:
        try:
            resp = requests.post(f"{self.base_url}/pre-checks/add-node", json=node_data)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"pre_check_add_node failed: {e}")
            raise

    def mgmt_add_node(self, mgmt_action: str, mgmt_data: dict) -> dict:
        try:
            payload = {"mgmt_action": mgmt_action, "mgmt_data": mgmt_data}
            resp = requests.post(f"{self.base_url}/pre-checks/add-node/mgmt", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"mgmt_add_node failed: {e}")
            raise

    def join_node(self, node_data: dict, mode: str = "local_network", custom_ip: str = None) -> dict:
        try:
            payload = {
                "node_data": node_data,
                "mode": mode
            }
            if custom_ip:
                payload["custom_ip"] = custom_ip

            resp = requests.post(f"{self.base_url}/join-node", json=payload)
            logger.info("join response message: %s", resp.json())

            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"join_node failed: {e}")
            raise

    def pre_check_remove_node(self, node_id: str) -> dict:
        try:
            payload = {"node_id": node_id}
            resp = requests.post(f"{self.base_url}/pre-checks/remove-node", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"pre_check_remove_node failed: {e}")
            raise

    def mgmt_remove_node(self, mgmt_action: str, mgmt_data: dict) -> dict:
        try:
            payload = {"mgmt_action": mgmt_action, "mgmt_data": mgmt_data}
            resp = requests.post(f"{self.base_url}/pre-checks/remove-node/mgmt", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"mgmt_remove_node failed: {e}")
            raise

    def remove_node(self, node_id: str) -> dict:
        try:
            payload = {"node_id": node_id}
            resp = requests.post(f"{self.base_url}/remove-node", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"remove_node failed: {e}")
            raise
    
    def sync_cluster(self) -> dict:
        try:
            resp = requests.post(f"{self.base_url}/sync-cluster")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"sync node failed: {e}")
            raise
