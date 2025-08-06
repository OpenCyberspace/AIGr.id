from kubernetes import client, config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class K8sPodLogsFetcher:
    def __init__(self, namespace="blocks", container_name="instance"):
        self.namespace = namespace
        self.container_name = container_name

        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration.")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Loaded local kubeconfig.")

        self.core_v1 = client.CoreV1Api()

    def get_logs_by_instance_id(self, instance_id, tail_lines=100):
        label_selector = f"instanceID={instance_id}"

        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            ).items

            if not pods:
                raise Exception(f"No pods found with instanceID={instance_id}")

            pod_name = pods[0].metadata.name
            logger.info(f"Fetching logs from pod: {pod_name}")

            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.namespace,
                container=self.container_name,
                tail_lines=tail_lines
            )
            return logs

        except Exception as e:
            logger.error(f"Error fetching logs for instanceID={instance_id}: {e}")
            return None

    def get_logs_by_block_id(self, block_id, tail_lines=100):
        label_selector = f"blockID={block_id}"
        logs_map = {}

        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            ).items

            if not pods:
                raise Exception(f"No pods found with blockID={block_id}")

            for pod in pods:
                pod_name = pod.metadata.name
                try:
                    log_output = self.core_v1.read_namespaced_pod_log(
                        name=pod_name,
                        namespace=self.namespace,
                        container=self.container_name,
                        tail_lines=tail_lines
                    )
                    logs_map[pod_name] = log_output
                except Exception as e:
                    logger.warning(f"Failed to get logs from pod {pod_name}: {e}")
                    logs_map[pod_name] = f"<error: {e}>"

            return logs_map

        except Exception as e:
            logger.error(f"Error fetching logs for blockID={block_id}: {e}")
            return {}
