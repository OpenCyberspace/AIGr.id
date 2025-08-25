from kubernetes import client, config
import logging
from .cluster_init import ClusterNodeInventory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def label_nodes_with_name():
   
    try:
        config.load_incluster_config()
        v1 = client.CoreV1Api()

        nodes = v1.list_node().items
        logger.info(f"Found {len(nodes)} nodes in the cluster.")

        for node in nodes:
            node_name = node.metadata.name
            label_value = node_name  # nodeID will be node_name
            body = {
                "metadata": {
                    "labels": {
                        "nodeID": label_value
                    }
                }
            }

            logger.info(f"Labeling node '{node_name}' with nodeID={label_value}")
            v1.patch_node(name=node_name, body=body)

        logger.info("All nodes labeled successfully.")
    except Exception as e:
        logger.error(f"Failed to label nodes: {e}")
        raise

def sync_cluster_nodes():
    inventory = ClusterNodeInventory()
    inventory.sync_node()