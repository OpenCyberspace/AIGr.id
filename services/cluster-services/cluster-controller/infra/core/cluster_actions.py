import os
from .cluster_db import ClusterClient
from .policy_sandbox import LocalPolicyEvaluator

from .cluster_db import ClusterClient
from .metrics import get_cluster_metrics_collector

'''
const clusterSchema = new Schema({
    id: { type: String, required: true, unique: true },
    regionId: { type: String, required: true },
    nodes: {
        count: { type: Number, required: true },
        nodeData: [{ type: Schema.Types.Mixed, required: false }]
    },
    gpus: {
        count: { type: Number, required: true },
        memory: { type: Number, required: true }
    },
    vcpus: {
        count: { type: Number, required: true }
    },
    memory: { type: Number, required: true },
    swap: { type: Number, required: true },
    storage: {
        disks: { type: Number, required: true },
        size: { type: Number, required: true }
    },
    network: {
        interfaces: { type: Number, required: true },
        txBandwidth: { type: Number, required: true },
        rxBandwidth: { type: Number, required: true }
    },
    config: { type: Schema.Types.Mixed, required: false },
    tags: { type: [String], required: true },
    clusterMetadata: { type: Schema.Types.Mixed, required: true },
    reputation: { type: Number, required: true },
});

'''


class ClusterActions:

    def __init__(self, actions_policies_map: dict) -> None:
        self.actions_policies_map = actions_policies_map
        self.cluster_db = ClusterClient()
        self.policy_execution_mode = os.getenv(
            "POLICY_EXECUTION_MODE", "local")
        self.cluster_id = os.getenv("CLUSTER_ID")

    def add_node_to_cluster(self, node_data: dict):

        try:
            if 'add_node' in self.actions_policies_map:
                policy_rule = LocalPolicyEvaluator(
                    self.actions_policies_map['add_node'],
                    settings={
                        "get_metrics": get_cluster_metrics_collector()
                    }
                )

                # cluster data:
                ret, cluster = ClusterClient().read_cluster(self.cluster_id)
                if not ret:
                    raise Exception(str(cluster))

                result = policy_rule.execute_policy_rule({
                    "cluster_data": cluster,
                    "node_data": node_data
                })

                if not result['allowed']:
                    return {"success": False, "message": result["message"]}

                modified_node_data = result.get('updated_node_data', None)
                if modified_node_data:
                    node_data = modified_node_data

            # Retrieve the cluster data
            cluster_id = os.getenv("CLUSTER_ID")
            ret, cluster_data = self.cluster_db.read_cluster(cluster_id)
            if not ret:
                raise Exception(
                    f"Failed to fetch cluster data: {cluster_data}")

            # Get current nodes list and add the new node
            existing_nodes = cluster_data.get("nodes", {}).get("nodeData", [])
            updated_nodes = existing_nodes + [node_data]

            # Recalculate aggregate values based on all nodes
            total_gpus = sum(node["gpus"]["count"] for node in updated_nodes)
            total_gpu_memory = sum(node["gpus"]["memory"]
                                   for node in updated_nodes)
            total_vcpus = sum(node["vcpus"]["count"] for node in updated_nodes)
            total_memory = sum(node["memory"] for node in updated_nodes)
            total_swap = sum(node["swap"] for node in updated_nodes)
            total_storage_disks = sum(node["storage"]["disks"]
                                      for node in updated_nodes)
            total_storage_size = sum(node["storage"]["size"]
                                     for node in updated_nodes)
            total_network_interfaces = sum(
                node["network"]["interfaces"] for node in updated_nodes)
            total_tx_bandwidth = sum(
                node["network"]["txBandwidth"] for node in updated_nodes)
            total_rx_bandwidth = sum(
                node["network"]["rxBandwidth"] for node in updated_nodes)

            model_names_set = set()
            for node in updated_nodes:
                model_names_set.update(node["gpus"].get("modelNames", []))

            # Prepare update payload
            updated_cluster_data = {
                "$set": {
                    "nodes.count": len(updated_nodes),
                    "nodes.nodeData": updated_nodes,
                    "gpus.count": total_gpus,
                    "gpus.memory": total_gpu_memory,
                    "gpus.modelNames": list(model_names_set),
                    "vcpus.count": total_vcpus,
                    "memory": total_memory,
                    "swap": total_swap,
                    "storage.disks": total_storage_disks,
                    "storage.size": total_storage_size,
                    "network.interfaces": total_network_interfaces,
                    "network.txBandwidth": total_tx_bandwidth,
                    "network.rxBandwidth": total_rx_bandwidth
                }
            }

            # Update cluster in DB
            update_success, response = self.cluster_db.update_cluster(
                cluster_id, updated_cluster_data)

            if not update_success:
                raise Exception(f"Failed to update cluster: {response}")

            return {"success": True, "data": response}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def remove_node_from_cluster(self, node_id: str):

        try:
            if "remove_node" in self.actions_policies_map:
                policy_rule = LocalPolicyEvaluator(
                    self.actions_policies_map["remove_node"],
                    settings={
                        "get_metrics": get_cluster_metrics_collector()
                    }
                )

                ret, cluster = ClusterClient().read_cluster(self.cluster_id)
                if not ret:
                    raise Exception(str(cluster))

                result = policy_rule.execute_policy_rule({
                    "cluster_data": cluster,
                    "node_id": node_id
                })

                if not result["allowed"]:
                    return {"success": False, "message": result["message"]}

            # Retrieve the cluster data
            cluster_id = os.getenv("CLUSTER_ID")
            ret, cluster_data = self.cluster_db.read_cluster(cluster_id)
            if not ret:
                raise Exception("Failed to fetch cluster data")

            # Get the existing nodes list and filter out the node
            existing_nodes = cluster_data.get("nodes", {}).get("nodeData", [])
            updated_nodes = [
                node for node in existing_nodes if node["id"] != node_id]

            if len(existing_nodes) == len(updated_nodes):
                return {"success": False, "message": f"Node {node_id} not found in cluster"}

            # Recalculate aggregate values based on remaining nodes
            total_gpus = sum(node["gpus"]["count"] for node in updated_nodes)
            total_gpu_memory = sum(node["gpus"]["memory"]
                                   for node in updated_nodes)
            total_vcpus = sum(node["vcpus"]["count"] for node in updated_nodes)
            total_memory = sum(node["memory"] for node in updated_nodes)
            total_swap = sum(node["swap"] for node in updated_nodes)
            total_storage_disks = sum(node["storage"]["disks"]
                                      for node in updated_nodes)
            total_storage_size = sum(node["storage"]["size"]
                                     for node in updated_nodes)
            total_network_interfaces = sum(
                node["network"]["interfaces"] for node in updated_nodes)
            total_tx_bandwidth = sum(
                node["network"]["txBandwidth"] for node in updated_nodes)
            total_rx_bandwidth = sum(
                node["network"]["rxBandwidth"] for node in updated_nodes)

            model_names_set = set()
            for node in updated_nodes:
                model_names_set.update(node["gpus"].get("modelNames", []))

            # Prepare update payload
            updated_cluster_data = {
                "$set": {
                    "nodes.count": len(updated_nodes),
                    "nodes.nodeData": updated_nodes,
                    "gpus.count": total_gpus,
                    "gpus.memory": total_gpu_memory,
                    "gpus.modelNames": list(model_names_set),
                    "vcpus.count": total_vcpus,
                    "memory": total_memory,
                    "swap": total_swap,
                    "storage.disks": total_storage_disks,
                    "storage.size": total_storage_size,
                    "network.interfaces": total_network_interfaces,
                    "network.txBandwidth": total_tx_bandwidth,
                    "network.rxBandwidth": total_rx_bandwidth
                }
            }

            # Update cluster in DB
            update_success, response = self.cluster_db.update_cluster(
                cluster_id, updated_cluster_data)

            if not update_success:
                raise Exception(f"Failed to update cluster: {response}")

            return {"success": True,  "data": response}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_cluster_data(self):
        try:
            cluster_id = os.getenv("CLUSTER_ID")
            ret, cluster_data = self.cluster_db.read_cluster(cluster_id)
            if not ret:
                raise Exception("failed to read cluster data")

            return {"success": True, "data": cluster_data}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def update_cluster_data(self, update_data: dict):
        try:
            if not isinstance(update_data, dict):
                raise ValueError("update_data must be a dictionary")

            cluster_id = os.getenv("CLUSTER_ID")
            if not cluster_id:
                raise Exception("CLUSTER_ID is not set in the environment")

            update_success, response = self.cluster_db.update_cluster(
                cluster_id, {"$set": update_data})

            if not update_success:
                raise Exception(f"Failed to update cluster: {response}")

            return {"success": True, "data": response}

        except Exception as e:
            return {"success": False, "message": str(e)}
