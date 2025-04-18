import requests

from .blocks import BlocksClient
from .cluster_controller import get_cluster_mgmt_connection_url


class ServiceMgmtClient:
    def __init__(self, base_url="base_url"):
        self.base_url = base_url

    def execute_mgmt_command(self, block_id, service, mgmt_action, mgmt_data=None):
        url = f"{self.base_url}/mgmt"
        payload = {
            "block_id": block_id,
            "service": service,
            "mgmt_action": mgmt_action,
            "mgmt_data": mgmt_data or {}
        }

        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "message": str(e)}


class BlockManagementService:

    def __init__(self) -> None:
        self.block_client = BlocksClient()

    def execute_mgmt_command(self, block_id: str, service: str, mgmt_command: str, mgmt_data: dict):
        try:

            block = self.block_client.get_block_by_id(block_id)
            cluster = block.get('cluster', None)

            if not cluster:
                raise Exception("cluster data not defined in the block")

            cluster_id = cluster['id']
            mgmt_connection_url = get_cluster_mgmt_connection_url(cluster_id)

            server = ServiceMgmtClient(base_url=mgmt_connection_url)
            result = server.execute_mgmt_command(
                block_id, service, mgmt_command, mgmt_data)

            return result

        except Exception as e:
            raise e

    def execute_mgmt_command_cluster(self, cluster_id: str, service: str, mgmt_command: str, mgmt_data: dict):
        try:

            mgmt_connection_url = get_cluster_mgmt_connection_url(cluster_id)

            server = ServiceMgmtClient(base_url=mgmt_connection_url)
            result = server.execute_mgmt_command("", service, mgmt_command, mgmt_data)
            return result

        except Exception as e:
            raise e
