from kubernetes import client, config
import os


def detect_node_id():
    try:
        config.load_incluster_config()
    except Exception as e_in_cluster:
        try:
            config.load_kube_config()
        except Exception as e_default:
            raise RuntimeError(
                "Failed to load Kubernetes configuration: "
                f"In-cluster error: {e_in_cluster}, Default config error: {e_default}"
            )

    # Create API client
    try:
        v1 = client.CoreV1Api()

        # Get the node name from the Downward API environment variable
        node_name = os.getenv("KUBERNETES_NODE_NAME")

        if not node_name:
            raise ValueError(
                "KUBERNETES_NODE_NAME environment variable not set.")

        # Fetch the node object
        node = v1.read_node(node_name)

        # Get the specific node label "nodeId"
        node_id = node.metadata.labels.get("nodeID", None)
        if not node_id:
            node_id = os.getenv("NODE_ID", "default-node")

        return node_id
    except Exception as e:
        return ""
