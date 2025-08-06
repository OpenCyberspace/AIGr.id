from kubernetes import client, config
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class K8sNodePortManager:
    def __init__(self):
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.namespace = "blocks"

    def _get_target_services(self, block_id):
        label_selector = f"blockID={block_id}"
        try:
            services = self.v1.list_namespaced_service(
                namespace=self.namespace, label_selector=label_selector
            )
            filtered_services = [
                svc for svc in services.items
                if svc.metadata.labels.get("instanceID") != "executor"
            ]
            return filtered_services
        except Exception as e:
            logger.error(f"Error fetching services: {e}")
            return []

    def enable_streaming_port(self, block_id):
        services = self._get_target_services(block_id)
        for svc in services:
            modified = False
            spec = svc.spec
            for port in spec.ports:
                if port.name == "ws":
                    if port.node_port:
                        logger.info(f"Service {svc.metadata.name} already exposes node port {port.node_port} on 'ws'")
                    else:
                        port.node_port = None  # Let Kubernetes allocate a port
                        port.target_port = port.port
                        modified = True
            if modified:
                try:
                    spec.type = "NodePort"
                    self.v1.patch_namespaced_service(
                        name=svc.metadata.name,
                        namespace=self.namespace,
                        body={"spec": spec}
                    )
                    logger.info(f"Enabled NodePort for service {svc.metadata.name} on 'ws' port")
                except Exception as e:
                    logger.error(f"Failed to patch service {svc.metadata.name}: {e}")

    def disable_streaming_port(self, block_id):
        services = self._get_target_services(block_id)
        for svc in services:
            modified = False
            spec = svc.spec
            for port in spec.ports:
                if port.name == "ws" and port.node_port:
                    port.node_port = None
                    modified = True
            if modified and spec.type == "NodePort":
                try:
                    spec.type = "ClusterIP"
                    self.v1.patch_namespaced_service(
                        name=svc.metadata.name,
                        namespace=self.namespace,
                        body={"spec": spec}
                    )
                    logger.info(f"Disabled NodePort for service {svc.metadata.name} on 'ws' port")
                except Exception as e:
                    logger.error(f"Failed to patch service {svc.metadata.name}: {e}")

def get_block_streaming_url(block_data, instance_id):
    try:

        block_id = block_data['id']
        cluster_data = block_data["cluster"]
        config2 = cluster_data.get('config', {})

        logging.info(f"cluster data: {cluster_data}, config2: {config2}")

        ip = config2.get('publicHostname', '')

        if len(ip) == 0:
            raise Exception("Public gateway URL not defined")

        if type(ip) == list and len(ip) > 0:
            ip = ip[0]

        # Load config and setup API
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()

        v1 = client.CoreV1Api()
        label_selector = f"blockID={block_id},instanceID={instance_id}"
        services = v1.list_namespaced_service(
            namespace="blocks", label_selector=label_selector
        )

        for svc in services.items:
            for port in svc.spec.ports:
                if port.name == "ws" and port.node_port:
                    return f"ws://{ip}:{port.node_port}"

        raise Exception("Streaming port not enabled or service not found")

    except Exception as e:
        raise Exception(f"Failed to get streaming URL: {e}")


def check_is_streaming_enabled(block_id):
    try:
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()

        v1 = client.CoreV1Api()
        label_selector = f"blockID={block_id}"
        services = v1.list_namespaced_service(namespace="blocks", label_selector=label_selector)

        for svc in services.items:
            instance_id = svc.metadata.labels.get("instanceID", "")
            if instance_id == "executor":
                continue

            for port in svc.spec.ports:
                if port.name == "ws" and port.node_port:
                    return True

        return False

    except Exception as e:
        raise Exception(f"Failed to check streaming status: {e}")