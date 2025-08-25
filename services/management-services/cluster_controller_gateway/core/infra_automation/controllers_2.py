import os
import time
import logging
from typing import Dict, Optional, List

from kubernetes import client, config
from kubernetes.client import ApiException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class ControllersStackManager:

    def __init__(
        self,
        kube_config_data: dict,
        namespace: str = "controllers",
        membership_image: str = "34.58.1.86:31280/cluster/membership:latest",
        grpc_proxy_image: str = "34.58.1.86:31280/cluster/rpc:latest",
        membership_node_port: int = 30501,
        grpc_proxy_node_port: int = 32000,
        cluster_id: str = "gcp-cluster-2",
        cluster_metrics_service_url: str = "http://metrics-writer-svc.metrics.svc.cluster.local:5000",
        policy_db_url: str = "http://34.58.1.86:30102",
        policy_execution_mode: str = "local",
        cluster_service_url: str = "http://34.58.1.86:30101",
    ):
        logger.info("Initializing ControllersStackManager...")
        config.load_kube_config_from_dict(kube_config_data)
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()

        self.namespace = namespace

        self.membership_deploy = "membership-server"
        self.membership_svc = "membership-server-svc"
        self.membership_image = membership_image
        self.membership_port = 8080
        self.membership_node_port = membership_node_port

        self.grpc_deploy = "grpc-proxy"
        self.grpc_svc = "grpc-proxy"
        self.grpc_proxy_image = grpc_proxy_image
        self.grpc_proxy_port = 9000
        self.grpc_proxy_node_port = grpc_proxy_node_port

        self.cluster_id = cluster_id
        self.cluster_metrics_service_url = cluster_metrics_service_url
        self.policy_db_url = policy_db_url
        self.policy_execution_mode = policy_execution_mode
        self.cluster_service_url = cluster_service_url

    # ------------------------ public API ------------------------

    def create(self) -> Dict[str, str]:
        try:
            self._ensure_namespace(self.namespace)

            logger.info("Applying membership-server Deployment...")
            self._apply_membership_deployment()
            logger.info("Applying membership-server Service...")
            self._apply_membership_service()

            logger.info("Applying grpc-proxy Deployment...")
            self._apply_grpc_proxy_deployment()
            logger.info("Applying grpc-proxy Service...")
            self._apply_grpc_proxy_service()

            logger.info("Waiting for deployments to become ready...")
            self._wait_for_deployment(self.membership_deploy)
            self._wait_for_deployment(self.grpc_deploy)

            return {
                "namespace": self.namespace,
                "membership_deployment": "ready",
                "membership_service": "created/updated",
                "grpc_proxy_deployment": "ready",
                "grpc_proxy_service": "created/updated",
            }
        except Exception as e:
            logger.exception("Create failed")
            raise RuntimeError(f"Create failed: {e}")

    def remove(self) -> Dict[str, str]:
        results = {}
        try:
            logger.info("Deleting membership-server Service...")
            results["membership_service"] = self._delete_service(self.membership_svc)
            logger.info("Deleting membership-server Deployment...")
            results["membership_deployment"] = self._delete_deployment(self.membership_deploy)

            logger.info("Deleting grpc-proxy Service...")
            results["grpc_proxy_service"] = self._delete_service(self.grpc_svc)
            logger.info("Deleting grpc-proxy Deployment...")
            results["grpc_proxy_deployment"] = self._delete_deployment(self.grpc_deploy)

            return results
        except Exception as e:
            logger.exception("Remove failed")
            raise RuntimeError(f"Remove failed: {e}")

    # ------------------------ helpers: namespace ------------------------

    def _ensure_namespace(self, namespace: str) -> None:
        try:
            self.core_v1.read_namespace(name=namespace)
            logger.info("Namespace exists: %s", namespace)
        except ApiException as e:
            if e.status == 404:
                logger.info("Creating namespace: %s", namespace)
                body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
                self.core_v1.create_namespace(body)
            else:
                raise

    # ------------------------ helpers: deployments ------------------------

    def _apply_membership_deployment(self) -> None:
        env = [
            client.V1EnvVar(name="PYTHONUNBUFFERED", value="1"),
            client.V1EnvVar(name="CLUSTER_ID", value=self.cluster_id),
            client.V1EnvVar(name="CLUSTER_METRICS_SERVICE_URL", value=self.cluster_metrics_service_url),
            client.V1EnvVar(name="POLICY_DB_URL", value=self.policy_db_url),
            client.V1EnvVar(name="POLICY_EXECUTION_MODE", value=self.policy_execution_mode),
            client.V1EnvVar(name="CLUSTER_SERVICE_URL", value=self.cluster_service_url),
        ]

        container = client.V1Container(
            name="flask-container",
            image=self.membership_image,
            image_pull_policy="Always",
            env=env,
            ports=[client.V1ContainerPort(container_port=self.membership_port)],
        )

        pod_spec = client.V1PodSpec(
            service_account_name="default",
            containers=[container],
        )

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=self.membership_deploy, namespace=self.namespace),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": self.membership_deploy}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": self.membership_deploy}),
                    spec=pod_spec,
                ),
            ),
        )

        self._create_or_replace_deployment(deployment)

    def _apply_grpc_proxy_deployment(self) -> None:
        container = client.V1Container(
            name="proxy",
            image=self.grpc_proxy_image,
            image_pull_policy="Always",
            ports=[client.V1ContainerPort(container_port=self.grpc_proxy_port)],
        )

        pod_spec = client.V1PodSpec(containers=[container])

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=self.grpc_deploy, namespace=self.namespace),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": self.grpc_deploy}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": self.grpc_deploy}),
                    spec=pod_spec,
                ),
            ),
        )

        self._create_or_replace_deployment(deployment)

    def _create_or_replace_deployment(self, deployment: client.V1Deployment) -> None:
        name = deployment.metadata.name
        namespace = deployment.metadata.namespace
        try:
            existing = self.apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
            deployment.metadata.resource_version = existing.metadata.resource_version
            self.apps_v1.replace_namespaced_deployment(name=name, namespace=namespace, body=deployment)
            logger.info("Deployment updated: %s/%s", namespace, name)
        except ApiException as e:
            if e.status == 404:
                self.apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
                logger.info("Deployment created: %s/%s", namespace, name)
            else:
                logger.exception("Failed to apply deployment: %s/%s", namespace, name)
                raise

    # ------------------------ helpers: services ------------------------

    def _apply_membership_service(self) -> None:
        svc = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=self.membership_svc,
                namespace=self.namespace,
            ),
            spec=client.V1ServiceSpec(
                type="NodePort",
                selector={"app": self.membership_deploy},
                ports=[
                    client.V1ServicePort(
                        name="http",
                        protocol="TCP",
                        port=self.membership_port,
                        target_port=self.membership_port,
                        node_port=self.membership_node_port,
                    )
                ],
            ),
        )
        self._create_or_replace_service(svc, preserve_cluster_ip=True)

    def _apply_grpc_proxy_service(self) -> None:
        svc = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=self.grpc_svc,
                namespace=self.namespace,
            ),
            spec=client.V1ServiceSpec(
                type="NodePort",
                selector={"app": self.grpc_deploy},
                ports=[
                    client.V1ServicePort(
                        name="grpc",
                        protocol="TCP",
                        port=self.grpc_proxy_port,
                        target_port=self.grpc_proxy_port,
                        node_port=self.grpc_proxy_node_port,
                    )
                ],
            ),
        )
        self._create_or_replace_service(svc, preserve_cluster_ip=True)

    def _create_or_replace_service(self, service: client.V1Service, preserve_cluster_ip: bool = True) -> None:
        name = service.metadata.name
        namespace = service.metadata.namespace
        try:
            existing = self.core_v1.read_namespaced_service(name=name, namespace=namespace)
            if preserve_cluster_ip:
                service.spec.cluster_ip = existing.spec.cluster_ip
                service.spec.cluster_ips = getattr(existing.spec, "cluster_ips", None)
                service.spec.ip_families = getattr(existing.spec, "ip_families", None)
                service.spec.ip_family_policy = getattr(existing.spec, "ip_family_policy", None)
            service.metadata.resource_version = existing.metadata.resource_version
            self.core_v1.replace_namespaced_service(name=name, namespace=namespace, body=service)
            logger.info("Service updated: %s/%s", namespace, name)
        except ApiException as e:
            if e.status == 404:
                self.core_v1.create_namespaced_service(namespace=namespace, body=service)
                logger.info("Service created: %s/%s", namespace, name)
            else:
                logger.exception("Failed to apply service: %s/%s", namespace, name)
                raise

    # ------------------------ helpers: wait & delete ------------------------

    def _wait_for_deployment(self, name: str, timeout: int = 300) -> None:
        start = time.time()
        while time.time() - start < timeout:
            try:
                dep = self.apps_v1.read_namespaced_deployment(name=name, namespace=self.namespace)
                desired = dep.spec.replicas or 0
                available = dep.status.available_replicas or 0
                if available >= desired and desired > 0:
                    logger.info("Deployment ready: %s/%s (available=%s desired=%s)", self.namespace, name, available, desired)
                    return
            except ApiException as e:
                logger.warning("Read deployment %s failed: %s", name, e)
            time.sleep(2)
        raise TimeoutError(f"Deployment '{name}' did not become ready in {timeout} seconds")

    def _delete_deployment(self, name: str) -> str:
        try:
            self.apps_v1.delete_namespaced_deployment(name=name, namespace=self.namespace)
            logger.info("Deployment delete requested: %s/%s", self.namespace, name)
            return "deleted"
        except ApiException as e:
            if e.status == 404:
                logger.info("Deployment not found (skip): %s/%s", self.namespace, name)
                return "not-found"
            raise

    def _delete_service(self, name: str) -> str:
        try:
            self.core_v1.delete_namespaced_service(name=name, namespace=self.namespace)
            logger.info("Service delete requested: %s/%s", self.namespace, name)
            return "deleted"
        except ApiException as e:
            if e.status == 404:
                logger.info("Service not found (skip): %s/%s", self.namespace, name)
                return "not-found"
            raise
