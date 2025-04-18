from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import logging


class NamespaceScanner:
    def __init__(self, namespace: str):

        self.namespace = namespace
        try:
            config.load_incluster_config()
            logging.info("Loaded in-cluster Kubernetes configuration.")
        except config.ConfigException:
            try:
                config.load_kube_config()
                logging.info("Loaded default Kubernetes configuration.")
            except config.ConfigException as e:
                logging.error(f"Failed to load Kubernetes configuration: {e}")
                raise

        try:
            self.v1 = client.CoreV1Api()
        except Exception as e:
            logging.error(f"Failed to initialize Kubernetes API client: {e}")
            raise

    def get_failed_pods(self):

        failed_pods = []

        try:
            pods = self.v1.list_namespaced_pod(namespace=self.namespace)
            for pod in pods.items:
                try:
                    failure_reason = self._is_pod_failed(pod)
                    if failure_reason:
                        labels = pod.metadata.labels or {}
                        failed_pods.append({
                            "instanceId": labels.get("instanceID", "N/A"),
                            "blockId": labels.get("blockID", "N/A"),
                            "pod_name": pod.metadata.name,
                            "failure_reason": failure_reason,
                            "pod_data": {
                                "node_name": pod.spec.node_name,
                                "namespace": pod.metadata.namespace,
                                "restart_count": sum(cs.restart_count for cs in pod.status.container_statuses or []),
                                "conditions": [
                                    {"type": c.type, "status": c.status,
                                        "reason": c.reason}
                                    for c in pod.status.conditions or []
                                ]
                            }
                        })
                except Exception as e:
                    logging.error(
                        f"Error processing pod {pod.metadata.name}: {e}")
        except ApiException as e:
            logging.error(f"Error retrieving pods: {e}")
        except Exception as e:
            logging.error(f"Unexpected error retrieving pods: {e}")

        return failed_pods

    def _is_pod_failed(self, pod):

        try:
            if pod.status.phase in ["Failed", "Unknown"]:
                return "pod_failed"

            for container_status in pod.status.container_statuses or []:
                if container_status.state.terminated:
                    if container_status.state.terminated.exit_code != 0:
                        return "container_exit_nonzero"
                if container_status.state.waiting:
                    if container_status.state.waiting.reason in ["CrashLoopBackOff", "Error", "ImagePullBackOff", "CreateContainerConfigError"]:
                        return "container_waiting_error"

            if pod.status.phase == "Pending" and pod.status.conditions:
                pod_scheduled = next(
                    (c for c in pod.status.conditions if c.type == "PodScheduled"), None)
                if pod_scheduled and pod_scheduled.status == "False":
                    for container_status in pod.status.container_statuses or []:
                        if container_status.state and container_status.state.waiting and container_status.state.waiting.reason in ["ContainerCreating", "PodInitializing"]:
                            return False
                    logging.warning(
                        f"Pod {pod.metadata.name} is stuck in Pending state.")
                    return "pod_pending"

            if pod.status.conditions:
                for condition in pod.status.conditions:
                    if condition.type == "Ready" and condition.status == "Unknown" and condition.reason == "NodeLost":
                        logging.warning(
                            f"Pod {pod.metadata.name} is on a lost node.")
                        return "node_lost"
        except Exception as e:
            logging.error(
                f"Error checking pod status {pod.metadata.name}: {e}")

        return False


class NodesHealth:
    def __init__(self):
        try:
            config.load_incluster_config()
            logging.info("Loaded in-cluster Kubernetes configuration.")
        except config.ConfigException:
            try:
                config.load_kube_config()
                logging.info("Loaded default Kubernetes configuration.")
            except config.ConfigException as e:
                logging.error(f"Failed to load Kubernetes configuration: {e}")
                raise

        try:
            self.v1 = client.CoreV1Api()
        except Exception as e:
            logging.error(f"Failed to initialize Kubernetes API client: {e}")
            raise

    def get_healthy_nodes(self):
        healthy_nodes = []
        try:
            nodes = self.v1.list_node()
            for node in nodes.items:
                conditions = {cond.type: cond.status for cond in node.status.conditions}
                if conditions.get("Ready") == "True":
                    node_id = node.metadata.labels.get("nodeID", node.metadata.name)
                    healthy_nodes.append(node_id)
        except Exception as e:
            logging.error(f"Error retrieving healthy nodes: {e}")
            return []
        return healthy_nodes

    def get_nodes_status(self):
        nodes_info = []
        try:
            nodes = self.v1.list_node()
            for node in nodes.items:
                node_id = node.metadata.labels.get("nodeID", node.metadata.name)

                # Determine node health
                conditions = {cond.type: cond.status for cond in node.status.conditions}
                is_healthy = conditions.get("Ready") == "True"
                status = "healthy" if is_healthy else "unhealthy"

                # Convert CPU cores (millicores 'm' to full cores)
                def parse_cpu(value):
                    if value.endswith("m"):
                        return int(value[:-1]) / 1000
                    return int(value)

                total_cpu = parse_cpu(node.status.capacity.get("cpu", "0"))
                allocatable_cpu = parse_cpu(node.status.allocatable.get("cpu", "0"))
                cpu_usage_percent = round(((total_cpu - allocatable_cpu) / total_cpu) * 100, 2) if total_cpu > 0 else 0

                # Convert memory and storage to MB
                def to_mb(value):
                    try:
                        if value.endswith("Ki"):
                            return int(value[:-2]) // 1024
                        elif value.endswith("Mi"):
                            return int(value[:-2])
                        elif value.endswith("Gi"):
                            return int(value[:-2]) * 1024
                        elif value.endswith("Ti"):
                            return int(value[:-2]) * 1024 * 1024
                        elif value.isdigit():
                            return int(value) // (1024 * 1024)
                    except ValueError:
                        logging.error(f"Invalid memory/storage value: {value}")
                        return 0
                    return 0

                total_memory = to_mb(node.status.capacity.get("memory", "0Mi"))
                allocatable_memory = to_mb(node.status.allocatable.get("memory", "0Mi"))
                memory_usage_percent = round(((total_memory - allocatable_memory) / total_memory) * 100, 2) if total_memory > 0 else 0

                total_disk = to_mb(node.status.capacity.get("ephemeral-storage", "0"))
                allocatable_disk = to_mb(node.status.allocatable.get("ephemeral-storage", "0"))
                disk_usage_percent = round(((total_disk - allocatable_disk) / total_disk) * 100, 2) if total_disk > 0 else 0

                nodes_info.append({
                    "node_id": node_id,
                    "status": status,
                    "cpu_utilization_percent": cpu_usage_percent,
                    "memory": {
                        "total": total_memory,
                        "allocatable": allocatable_memory,
                        "usage_percent": memory_usage_percent
                    },
                    "disk": {
                        "total": total_disk,
                        "allocatable": allocatable_disk,
                        "usage_percent": disk_usage_percent
                    }
                })
        except Exception as e:
            logging.error(f"Error retrieving node statuses: {e}")
            return []
        return nodes_info







