import logging
from kubernetes import client, config
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExecutorInitializer:
    def __init__(self, cluster_config: dict, executor_id: str, max_processes: int):
        self.executor_id = executor_id
        self.namespace = os.getenv("EXECUTOR_NAMESPACE", "policies-system")
        self.container_image_name = os.getenv(
            "EXECUTOR_CONTAINER_IMAGE_NAME", "aiosv1/policies-executor_api:v1")
        self.max_processes = str(max_processes)
        self.deployment_name = f"executor-{executor_id}"
        self.service_name = f"executor-svc-{executor_id}"
        self.ambassador_mapping_name = f"executor-mapping-{executor_id}"

        try:
            self._load_cluster_config(cluster_config)
            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self.custom_api = client.CustomObjectsApi()
        except Exception as e:
            logger.error(f"Error loading cluster config: {e}")
            raise

    def _load_cluster_config(self, cluster_config):
        config.load_kube_config_from_dict(cluster_config)

    def create_executor(self):
        try:
            self._create_deployment()
            self._create_service()
            self._register_in_ambassador()
        except Exception as e:
            logger.error(f"Error creating executor: {e}")
            raise

    def _create_deployment(self):
        try:
            env_vars = [
                client.V1EnvVar(name="JOB_MANAGER_URL",
                                value=os.getenv("JOB_MANAGER_URL")),
                client.V1EnvVar(name="DB_URL", value=os.getenv("DB_URL")),
                client.V1EnvVar(name="DB_API_URL",
                                value=os.getenv("DB_API_URL")),
                client.V1EnvVar(name="DEFAULT_POLICY_CONTAINER_IMAGE", value=os.getenv(
                    "DEFAULT_POLICY_CONTAINER_IMAGE")),
                client.V1EnvVar(name="POLICY_DB_URL",
                                value=os.getenv("POLICY_DB_URL")),
                client.V1EnvVar(name="MAX_PROCESSES",
                                value=self.max_processes),
            ]

            container = client.V1Container(
                name=self.deployment_name,
                image=self.container_image_name,
                env=env_vars,
                ports=[
                    client.V1ContainerPort(container_port=10250)
                ]
            )

            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": self.deployment_name}),
                spec=client.V1PodSpec(containers=[container])
            )

            spec = client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"app": self.deployment_name}),
                template=template
            )

            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(
                    name=self.deployment_name, namespace=self.namespace),
                spec=spec
            )

            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)
            logger.info(
                f"Deployment {self.deployment_name} created successfully.")
        except Exception as e:
            logger.error(f"Error creating deployment: {e}")
            raise

    def _create_service(self):
        try:
            service = client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=self.service_name, namespace=self.namespace),
                spec=client.V1ServiceSpec(
                    selector={"app": self.deployment_name},
                    ports=[client.V1ServicePort(port=10250, target_port=10250, node_port=30900)],
                    type="NodePort"
                )
            )

            self.core_v1.create_namespaced_service(
                namespace=self.namespace, body=service)
            logger.info(f"Service {self.service_name} created successfully.")
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            raise

    def _register_in_ambassador(self):
        try:
            ambassador_mapping = {
                "apiVersion": "getambassador.io/v2",
                "kind": "Mapping",
                "metadata": {"name": self.ambassador_mapping_name, "namespace": self.namespace},
                "spec": {
                    "prefix": f"/executor/{self.executor_id}",
                    "service": f"{self.service_name}.{self.namespace}.svc.cluster.local:10250",
                },
            }

            self.custom_api.create_namespaced_custom_object(
                group="getambassador.io",
                version="v2",
                namespace=self.namespace,
                plural="mappings",
                body=ambassador_mapping,
            )
            logger.info(
                f"Ambassador mapping {self.ambassador_mapping_name} registered successfully.")
        except Exception as e:
            logger.error(f"Error registering ambassador mapping: {e}")
            raise

    def remove_executor(self):
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=self.deployment_name, namespace=self.namespace)
            logger.info(
                f"Deployment {self.deployment_name} deleted successfully.")

            self.core_v1.delete_namespaced_service(
                name=self.service_name, namespace=self.namespace)
            logger.info(f"Service {self.service_name} deleted successfully.")

            self.custom_api.delete_namespaced_custom_object(
                group="getambassador.io",
                version="v2",
                namespace=self.namespace,
                plural="mappings",
                name=self.ambassador_mapping_name
            )
            logger.info(
                f"Ambassador mapping {self.ambassador_mapping_name} deleted successfully.")
        except Exception as e:
            logger.error(f"Error removing executor: {e}")
            raise
