import logging
import os
from kubernetes import client, config
from kubernetes.client.rest import Exception

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TASK_DB_STATUS_UPDATE_URL=os.getenv("TASK_DB_STATUS_UPDATE_URL")
MODEL_LAYERS_REGISTRY_URL=os.getenv("MODEL_LAYERS_REGISTRY_URL")
BLOCK_DB_URL=os.getenv("BLOCKS_DB_URL")

class K8SplitRunnerAPI:
    def __init__(self, kube_config_dict: dict, namespace="split-executor"):
        try:
            config.load_kube_config_from_dict(kube_config_dict)
            logger.info("Loaded Kubernetes config from provided dictionary.")
        except Exception as e:
            logger.exception("Failed to load Kubernetes config from dict.")
            raise

        self.namespace = namespace
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self._ensure_namespace_exists()

    def _ensure_namespace_exists(self):
        try:
            self.core_v1.read_namespace(self.namespace)
            logger.info(f"Namespace '{self.namespace}' already exists.")
        except Exception as e:
            if e.status == 404:
                logger.info(f"Creating namespace '{self.namespace}'...")
                ns = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=self.namespace)
                )
                self.core_v1.create_namespace(ns)
            else:
                raise

    def deploy_split_runner_server(self, image="aiosv1/split-executor:v1", node_port=32286):
        deployment_name = "split-runner"
        service_name = "split-runner-service"

        container = client.V1Container(
            name="split-runner",
            image=image,
            ports=[client.V1ContainerPort(container_port=5000)],
            env=[
                client.V1EnvVar(
                    name="TASK_DB_STATUS_UPDATE_URL", value=TASK_DB_STATUS_UPDATE_URL
                ),
                client.V1EnvVar(
                    name="MODEL_LAYERS_REGISTRY_URL", value=MODEL_LAYERS_REGISTRY_URL
                ),
                client.V1EnvVar(
                    name="BLOCK_DB_URL", value=BLOCK_DB_URL
                )
            ]
        )

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
            spec=client.V1PodSpec(containers=[container])
        )

        spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": deployment_name}),
            template=template
        )

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=spec
        )

        try:
            self.apps_v1.read_namespaced_deployment(name=deployment_name, namespace=self.namespace)
            self.apps_v1.replace_namespaced_deployment(name=deployment_name, namespace=self.namespace, body=deployment)
            logger.info("Deployment updated.")
        except Exception as e:
            if e.status == 404:
                self.apps_v1.create_namespaced_deployment(namespace=self.namespace, body=deployment)
                logger.info("Deployment created.")
            else:
                raise

        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=service_name),
            spec=client.V1ServiceSpec(
                type="NodePort",
                selector={"app": deployment_name},
                ports=[
                    client.V1ServicePort(
                        port=5000,
                        target_port=5000,
                        node_port=node_port,
                        protocol="TCP"
                    )
                ]
            )
        )

        try:
            self.core_v1.read_namespaced_service(name=service_name, namespace=self.namespace)
            self.core_v1.replace_namespaced_service(name=service_name, namespace=self.namespace, body=service)
            logger.info("Service updated.")
        except Exception as e:
            if e.status == 404:
                self.core_v1.create_namespaced_service(namespace=self.namespace, body=service)
                logger.info("Service created.")
            else:
                raise
