from typing import Dict
from kubernetes import client
import os
import logging
from .cluster import ClusterClient

logger = logging.getLogger(__name__)


def update_cluster_with_new_node_data(node_data: dict) -> bool:

    try:
        cluster_id = os.getenv("CLUSTER_ID")
        if not cluster_id:
            logger.error("CLUSTER_ID environment variable not set.")
            return False

        logger.info(
            f"[cluster-update] Updating cluster '{cluster_id}' with new node ID: {node_data.get('id')}")
        ret, cluster_data = ClusterClient().read_cluster(cluster_id)
        if not ret:
            logger.error(
                f"[cluster-update] Failed to read cluster {cluster_id} from DB.")
            return False

        updated_nodes = cluster_data.get("nodes", {}).get("nodeData", [])
        updated_nodes.append(node_data)

        # Compute aggregates
        total_memory = sum(n.get("memory", 0) for n in updated_nodes)
        total_vcpus = sum(n.get("vcpus", {}).get("count", 0)
                          for n in updated_nodes)
        total_swap = sum(n.get("swap", 0) for n in updated_nodes)
        total_storage_disks = sum(n.get("storage", {}).get(
            "disks", 0) for n in updated_nodes)
        total_storage_size = sum(n.get("storage", {}).get(
            "size", 0) for n in updated_nodes)
        total_network_interfaces = sum(n.get("network", {}).get(
            "interfaces", 0) for n in updated_nodes)
        total_tx_bandwidth = sum(n.get("network", {}).get(
            "txBandwidth", 0) for n in updated_nodes)
        total_rx_bandwidth = sum(n.get("network", {}).get(
            "rxBandwidth", 0) for n in updated_nodes)
        total_gpus = sum(n.get("gpus", {}).get("count", 0)
                         for n in updated_nodes)
        total_gpu_memory = sum(n.get("gpus", {}).get("memory", 0)
                               for n in updated_nodes)

        model_names_set = set()
        for n in updated_nodes:
            model_names_set.update(n.get("gpus", {}).get("modelNames", []))

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

        success, response = ClusterClient().update_cluster(
            cluster_id, updated_cluster_data)
        if success:
            logger.info(
                f"[cluster-update] Cluster '{cluster_id}' updated successfully with new node.")
        else:
            logger.error(
                f"[cluster-update] Failed to update cluster '{cluster_id}': {response}")

        return success

    except Exception as e:
        logger.exception("[cluster-update] Exception during cluster update")
        return False


def remove_node_from_cluster(node_id: str) -> bool:

    try:
        cluster_id = os.getenv("CLUSTER_ID")
        if not cluster_id:
            logger.error("CLUSTER_ID environment variable not set.")
            return False

        logger.info(
            f"[cluster-update] Removing node '{node_id}' from cluster '{cluster_id}'")
        ret, cluster_data = ClusterClient().read_cluster(cluster_id)
        if not ret:
            logger.error(
                f"[cluster-update] Failed to read cluster {cluster_id} from DB.")
            return False

        original_nodes = cluster_data.get("nodes", {}).get("nodeData", [])
        updated_nodes = [n for n in original_nodes if n.get("id") != node_id]

        if len(updated_nodes) == len(original_nodes):
            logger.warning(
                f"[cluster-update] Node '{node_id}' not found in cluster — no update needed.")
            return True  # no-op, but not a failure

        # Recompute aggregates
        total_memory = sum(n.get("memory", 0) for n in updated_nodes)
        total_vcpus = sum(n.get("vcpus", {}).get("count", 0)
                          for n in updated_nodes)
        total_swap = sum(n.get("swap", 0) for n in updated_nodes)
        total_storage_disks = sum(n.get("storage", {}).get(
            "disks", 0) for n in updated_nodes)
        total_storage_size = sum(n.get("storage", {}).get(
            "size", 0) for n in updated_nodes)
        total_network_interfaces = sum(n.get("network", {}).get(
            "interfaces", 0) for n in updated_nodes)
        total_tx_bandwidth = sum(n.get("network", {}).get(
            "txBandwidth", 0) for n in updated_nodes)
        total_rx_bandwidth = sum(n.get("network", {}).get(
            "rxBandwidth", 0) for n in updated_nodes)
        total_gpus = sum(n.get("gpus", {}).get("count", 0)
                         for n in updated_nodes)
        total_gpu_memory = sum(n.get("gpus", {}).get("memory", 0)
                               for n in updated_nodes)

        model_names_set = set()
        for n in updated_nodes:
            model_names_set.update(n.get("gpus", {}).get("modelNames", []))

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

        success, response = ClusterClient().update_cluster(
            cluster_id, updated_cluster_data)
        if success:
            logger.info(
                f"[cluster-update] Node '{node_id}' removed and cluster '{cluster_id}' updated successfully.")
        else:
            logger.error(
                f"[cluster-update] Failed to update cluster '{cluster_id}': {response}")

        return success

    except Exception as e:
        logger.exception("[cluster-update] Exception during node removal")
        return False
