from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time

class MetricsCollectorManager:
    def __init__(self, kube_config_data: str, cluster_id: str, collect_interval: str, redis_host: str, globals={}, cluster_data={}):
        config.load_kube_config_from_dict(kube_config_data)
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = "metrics"
        self.daemonset_name = "metrics-collector"
        self.cluster_id = cluster_id
        self.collect_interval = collect_interval
        self.redis_host = redis_host
        self.globals = globals
        self.cluster_data = cluster_data

        self.metrics_redis_host = "metrics-writer-svc.metrics.svc.cluster.local"

    def get_metrics_collect_interval(self):
        try:

            cfg = self.cluster_data['config']
            return str(cfg.get("clusterMetricsCollectInterval", 30))
            
        except Exception as e:
            raise e

    def create(self):
        try:

            metrics_collect_interval = self.get_metrics_collect_interval()

            daemonset = client.V1DaemonSet(
                metadata=client.V1ObjectMeta(name=self.daemonset_name),
                spec=client.V1DaemonSetSpec(
                    selector=client.V1LabelSelector(match_labels={"app": self.daemonset_name}),
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(labels={"app": self.daemonset_name}),
                        spec=client.V1PodSpec(
                            host_network=True,
                            containers=[
                                client.V1Container(
                                    name="metrics-collector",
                                    image="aiosv1/metrics-collector:v1",
                                    env=[
                                        client.V1EnvVar(name="CLUSTER_ID", value=self.cluster_id),
                                        client.V1EnvVar(name="COLLECT_INTERVAL", value=metrics_collect_interval),
                                        client.V1EnvVar(name="METRICS_REDIS_HOST", value=self.metrics_redis_host),
                                        client.V1EnvVar(
                                            name="KUBERNETES_NODE_NAME",
                                            value_from=client.V1EnvVarSource(
                                                field_ref=client.V1ObjectFieldSelector(field_path="spec.nodeName")
                                            )
                                        ),
                                        client.V1EnvVar(name="NVIDIA_VISIBLE_DEVICES", value="all"),
                                        client.V1EnvVar(name="NVIDIA_DRIVER_CAPABILITIES", value="all") 
                                    ],
                                    security_context=client.V1SecurityContext(privileged=True),
                                    volume_mounts=[
                                        client.V1VolumeMount(name="host-proc", mount_path="/host/proc", read_only=True),
                                        client.V1VolumeMount(name="host-sys", mount_path="/host/sys", read_only=True),
                                    ]
                                )
                            ],
                            volumes=[
                                client.V1Volume(
                                    name="host-proc",
                                    host_path=client.V1HostPathVolumeSource(path="/proc")
                                ),
                                client.V1Volume(
                                    name="host-sys",
                                    host_path=client.V1HostPathVolumeSource(path="/sys")
                                ),
                            ],
                            tolerations=[client.V1Toleration(operator="Exists")],
                            node_selector={"kubernetes.io/os": "linux"}
                        )
                    )
                )
            )
            self.apps_v1.create_namespaced_daemon_set(namespace=self.namespace, body=daemonset)

            # Wait for DaemonSet readiness
            self._wait_for_daemonset()
        except ApiException as e:
            raise RuntimeError(f"Kubernetes API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during creation: {e}")

    def remove(self):
        try:
            self.apps_v1.delete_namespaced_daemon_set(name=self.daemonset_name, namespace=self.namespace)
        except ApiException as e:
            raise RuntimeError(f"Kubernetes API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during removal: {e}")

    def _wait_for_daemonset(self, timeout=300):
        """Wait for the DaemonSet to be fully scheduled and ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            daemonset = self.apps_v1.read_namespaced_daemon_set(name=self.daemonset_name, namespace=self.namespace)
            if daemonset.status.number_ready == daemonset.status.desired_number_scheduled:
                return
            time.sleep(2)
        raise TimeoutError(f"DaemonSet '{self.daemonset_name}' did not become ready within {timeout} seconds.")
