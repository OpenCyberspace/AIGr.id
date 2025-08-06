import logging
from kubernetes import client, config
from .cluster import ClusterClient
from .update import update_cluster_with_new_node_data, remove_node_from_cluster
import secrets
import string
import base64
import os
import time
import threading

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_cluster_ip(mode="local_network", ip_name=None):
    try:
        cluster_id = os.getenv("CLUSTER_ID")
        logger.info(f"Fetching cluster IP for cluster ID: {cluster_id}")

        client_obj = ClusterClient()
        ret, cluster_data = client_obj.read_cluster(cluster_id)
        if not ret:
            msg = f"Error retrieving cluster data for cluster={cluster_id}"
            logger.error(msg)
            raise Exception(msg)

        config_data = cluster_data.get('config', {})
        cert_hash = config_data.get('certHash')
        if not cert_hash:
            msg = "cert hash not provided by the cluster"
            logger.error(msg)
            raise Exception(msg)

        if ip_name:
            logger.info(f"Looking for secondary IP with name: {ip_name}")
            if 'secondaryIPs' not in config_data:
                raise Exception("Cluster does not support secondary IPs")
            secondary_ip = config_data['secondaryIPs'].get(ip_name)
            if not secondary_ip:
                raise Exception(f"Secondary IP {ip_name} not provided")
            logger.info(f"Using secondary IP: {secondary_ip}")
            return secondary_ip, cert_hash

        if mode == "local_network":
            local_host_name = config_data.get('localNetworkHostName')
            if not local_host_name:
                raise Exception(
                    "Local LAN network IP not provided for the cluster")
            logger.info(f"Using local network hostname: {local_host_name}")
            return local_host_name, cert_hash
        else:
            public_host_name = config_data.get('publicHostname')
            if not public_host_name:
                raise Exception("Public IP not provided for the cluster")
            logger.info(f"Using public hostname: {public_host_name}")
            return public_host_name, cert_hash

    except Exception as e:
        logger.exception("Failed to get cluster IP")
        raise


def generate_join_command(mode="local_network", custom_ip=None):
    try:
        logger.info("Generating kubeadm join command")

        # Load Kubernetes API config
        logger.info("Loading in-cluster Kubernetes config")
        config.load_incluster_config()

        v1 = client.CoreV1Api()
        host, cert_hash = get_cluster_ip(mode, custom_ip)

        # Define static token values
        alphabet = string.ascii_lowercase + string.digits
        token_id = ''.join(secrets.choice(alphabet) for _ in range(6))
        token_secret = ''.join(secrets.choice(alphabet) for _ in range(16))
        token = f"{token_id}.{token_secret}"
        logger.info(f"Generated token ID: {token_id}")
        logger.info(f"Generated token secret: [REDACTED]")

        # Create bootstrap token secret
        secret_name = f"bootstrap-token-{token_id}"
        logger.info(f"Creating bootstrap token secret: {secret_name}")

        secret_body = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=secret_name,
                namespace="kube-system"
            ),
            type="bootstrap.kubernetes.io/token",
            data={
                "token-id": base64.b64encode(token_id.encode()).decode(),
                "token-secret": base64.b64encode(token_secret.encode()).decode(),
                "usage-bootstrap-authentication": base64.b64encode(b"true").decode(),
                "usage-bootstrap-signing": base64.b64encode(b"true").decode(),
                "auth-extra-groups": base64.b64encode(
                    b"system:bootstrappers:kubeadm:default-node-token"
                ).decode()
            }
        )

        try:
            v1.create_namespaced_secret(
                namespace="kube-system", body=secret_body)
            logger.info(f"Secret {secret_name} created successfully")
        except client.exceptions.ApiException as e:
            if e.status == 409:
                logger.warning(
                    f"Secret {secret_name} already exists, continuing")
            else:
                logger.exception("Error creating bootstrap secret")
                raise

        host = os.environ.get("CONTROL_PLANE_ADDRESS", host)
        port = "6443"
        join_cmd = (
            f"kubeadm join {host}:{port} "
            f"--token {token} "
            f"--discovery-token-ca-cert-hash sha256:{cert_hash}"
        )

        logger.info("Join command generated successfully")
        return join_cmd

    except Exception as e:
        logger.exception("Failed to generate join command")
        raise RuntimeError(f"Failed to generate join command: {str(e)}")


def wait_for_node_and_label(node_data: dict, expected_node_name: str, node_id_label: str = None, timeout: int = 300):

    def _wait_and_label():
        try:
            config.load_incluster_config()
            v1 = client.CoreV1Api()

            logger.info(
                f"Waiting for node '{expected_node_name}' to join and become Ready (timeout={timeout}s)...")
            start_time = time.time()

            while True:
                try:
                    node = v1.read_node(name=expected_node_name)
                    conditions = {
                        cond.type: cond.status for cond in node.status.conditions or []}
                    if conditions.get("Ready") == "True":
                        logger.info(f"Node '{expected_node_name}' is Ready.")
                        break
                except Exception as e:
                    logger.warning(f"Error during node polling: {e}")

                if time.time() - start_time > timeout:
                    logger.error(
                        f"Timeout: Node '{expected_node_name}' did not become Ready in {timeout}s.")
                    return

                time.sleep(5)

            # Label the node
            label_value = node_id_label or expected_node_name
            body = {
                "metadata": {
                    "labels": {
                        "nodeID": label_value
                    }
                }
            }

            logger.info(
                f"Labeling node '{expected_node_name}' with nodeID={label_value}")
            v1.patch_node(name=expected_node_name, body=body)

            logger.info("Node labeling complete. Proceeding with post-label functionality.")

            update_cluster_with_new_node_data(node_data)

        except Exception as e:
            logger.exception(f"Error in wait_for_node_and_label: {e}")

    thread = threading.Thread(target=_wait_and_label,
                              name=f"WaitForNode-{expected_node_name}")
    thread.daemon = True
    thread.start()
    return thread



def join_node(node_data, expected_node_name: str, mode="local_network", custom_ip=None, timeout=300) -> dict:
    
    try:
        logger.info(f"[join_node] Starting join process for node '{expected_node_name}'")

        join_cmd = generate_join_command(mode=mode, custom_ip=custom_ip)
        logger.info(f"[join_node] Join command generated for node '{expected_node_name}'")

        logger.info(f"[join_node] Starting waiter thread for node '{expected_node_name}'")
        wait_for_node_and_label(node_data, expected_node_name, node_id_label=expected_node_name, timeout=timeout)

        return {
            "success": True,
            "join_command": join_cmd,
            "message": f"Join command generated and waiter started for node '{expected_node_name}'"
        }

    except Exception as e:
        logger.exception("[join_node] Failed to generate join command or start waiter")
        return {
            "success": False,
            "error": str(e)
        }


def remove_node(node_id: str) -> dict:
 
    try:
        logger.info(f"[remove_node] Connecting to Kubernetes to remove node '{node_id}'")
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        policy = client.PolicyV1Api()

        # Step 1: Cordon the node
        logger.info(f"[remove_node] Cordoning node '{node_id}'")
        body = {
            "spec": {
                "unschedulable": True
            }
        }
        v1.patch_node(name=node_id, body=body)

        # Step 2: List all pods on the node
        pods = v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_id}")
        logger.info(f"[remove_node] Found {len(pods.items)} pods on node '{node_id}'")

        # Step 3: Evict pods (ignore DaemonSets and mirror pods)
        for pod in pods.items:
            if pod.metadata.owner_references:
                for ref in pod.metadata.owner_references:
                    if ref.kind == "DaemonSet":
                        logger.debug(f"Skipping DaemonSet pod: {pod.metadata.name}")
                        break
                else:
                    # Not a DaemonSet
                    evict_body = client.V1Eviction(
                        metadata=client.V1ObjectMeta(name=pod.metadata.name, namespace=pod.metadata.namespace),
                        delete_options=client.V1DeleteOptions(grace_period_seconds=30)
                    )
                    try:
                        logger.info(f"Evicting pod: {pod.metadata.namespace}/{pod.metadata.name}")
                        policy.create_namespaced_pod_eviction(
                            name=pod.metadata.name,
                            namespace=pod.metadata.namespace,
                            body=evict_body
                        )
                    except Exception as e:
                        logger.error(f"Failed to evict pod {pod.metadata.name}: {e}")
            else:
                logger.debug(f"Skipping mirror/static pod: {pod.metadata.name}")

        logger.info(f"[remove_node] Drain complete for node '{node_id}'")
        remove_node_from_cluster(node_id)
        return {
            "success": True,
            "message": f"Node '{node_id}' drained. Client can now reset the node."
        }
        
    except Exception as e:
        logger.exception(f"[remove_node] Unexpected error for node '{node_id}'")
        return {
            "success": False,
            "message": str(e)
        }
 