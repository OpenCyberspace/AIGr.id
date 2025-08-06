from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time


class MetricsDBCreator:
    def __init__(self, kube_config_data: str):
        config.load_kube_config_from_dict(kube_config_data)
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = "metrics"
        self.deployment_name = "cluster-metrics"
        self.service_name = "cluster-metrics-svc"

    def create(self):
        try:
            # Create Deployment
            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(name=self.deployment_name),
                spec=client.V1DeploymentSpec(
                    replicas=1,
                    selector=client.V1LabelSelector(
                        match_labels={"app": self.deployment_name}),
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(
                            labels={"app": self.deployment_name}),
                        spec=client.V1PodSpec(
                            containers=[
                                client.V1Container(
                                    name="mongodb",
                                    image="mongo:latest",
                                    ports=[client.V1ContainerPort(
                                        container_port=27017)],
                                    readiness_probe=client.V1Probe(
                                        tcp_socket=client.V1TCPSocketAction(
                                            port=27017),
                                        initial_delay_seconds=5,
                                        period_seconds=2
                                    )
                                )
                            ]
                        )
                    )
                )
            )
            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)

            # Create Service
            service = client.V1Service(
                metadata=client.V1ObjectMeta(name=self.service_name),
                spec=client.V1ServiceSpec(
                    selector={"app": self.deployment_name},
                    ports=[client.V1ServicePort(name="db",
                        port=27017, target_port=27017)],
                    type="ClusterIP"
                )
            )
            self.core_v1.create_namespaced_service(
                namespace=self.namespace, body=service)

            # Wait for DB readiness
            self._wait_for_db()
        except ApiException as e:
            raise RuntimeError(f"Kubernetes API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during creation: {e}")

    def remove(self):
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=self.deployment_name, namespace=self.namespace)
            self.core_v1.delete_namespaced_service(
                name=self.service_name, namespace=self.namespace)
        except ApiException as e:
            raise RuntimeError(f"Kubernetes API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during removal: {e}")

    def _wait_for_db(self, timeout=300):
        """Wait for MongoDB to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"app={self.deployment_name}")
            if not pods.items:
                time.sleep(2)
                continue

            pod = pods.items[0]
            if pod.status.phase == "Running" and all(
                c.ready for c in pod.status.container_statuses
            ):
                return
            time.sleep(2)
        raise TimeoutError(
            f"MongoDB deployment did not become ready within {timeout} seconds.")
