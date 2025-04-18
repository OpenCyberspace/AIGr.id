import os
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logging.basicConfig(level=logging.INFO)


class vDAGInfraManager:
    def __init__(self, deployment_name: str, vdag_uri: str, policy_execution_mode: str):
        self.deployment_name = deployment_name
        self.namespace = "vdags"
        self.image = os.getenv("VDAG_CONTROLLER_IMAGE_NAME",
                               "aiosv1/vdag-controller:v1")
        self.api = client.AppsV1Api()
        self.core_api = client.CoreV1Api()
        self.custom_api = client.CustomObjectsApi()

        try:
            config.load_incluster_config()
            logging.info("Loaded in-cluster Kubernetes config.")
        except Exception:
            try:
                config.load_kube_config()
                logging.info("Loaded kube config from local system.")
            except Exception as e:
                logging.error(f"Failed to load Kubernetes config: {e}")
                raise

        # Ensure namespace exists
        self.ensure_namespace()

        # Store environment variables
        self.env_vars = [
            client.V1EnvVar(name="VDAG_URI", value=vdag_uri),
            client.V1EnvVar(name="VDAG_ADHOC_INFERENCE_SERVER_URL", value=os.getenv(
                "VDAF_ADHOC_INFERENCE_SERVER_URL", "")),
            client.V1EnvVar(name="VDAG_DB_API_URL",
                            value=os.getenv("VDAG_DB_API_URL", "")),
            client.V1EnvVar(name="POLICY_SYSTEM_EXECUTOR_ID", value=os.getenv(
                "CLUSTER_DEFAULT_POLICY_EXECUTOR", "")),
            client.V1EnvVar(name="POLICY_EXECUTION_MODE",
                            value=policy_execution_mode),
            client.V1EnvVar(name="POLICY_DB_URL",
                            value=os.getenv("POLICY_DB_URL", ""))
        ]

    def ensure_namespace(self):
        try:
            self.core_api.read_namespace(name=self.namespace)
            logging.info(f"Namespace '{self.namespace}' already exists.")
        except ApiException as e:
            if e.status == 404:
                namespace_body = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=self.namespace)
                )
                self.core_api.create_namespace(body=namespace_body)
                logging.info(f"Namespace '{self.namespace}' created.")
            else:
                logging.error(f"Failed to check or create namespace: {e}")

    def create_controller(self, replicas=1):
        self.create_deployment(replicas)
        self.create_service()

    def remove_controller(self):
        self.delete_service()
        self.delete_deployment()

    def create_deployment(self, replicas=1):
        try:
            container = client.V1Container(
                name=self.deployment_name,
                image=self.image,
                ports=[
                    client.V1ContainerPort(container_port=50051),
                    client.V1ContainerPort(container_port=5000)
                ],
                env=self.env_vars
            )

            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": self.deployment_name}),
                spec=client.V1PodSpec(containers=[container])
            )

            spec = client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(
                    match_labels={"app": self.deployment_name}),
                template=template
            )

            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(
                    name=self.deployment_name, namespace=self.namespace),
                spec=spec
            )

            self.api.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)
            logging.info(f"Deployment {self.deployment_name} created.")
        except ApiException as e:
            logging.error(f"Failed to create deployment: {e}")

    def create_service(self):
        try:
            service_name = f"{self.deployment_name}-svc"
            service = client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=service_name, namespace=self.namespace),
                spec=client.V1ServiceSpec(
                    selector={"app": self.deployment_name},
                    ports=[
                        client.V1ServicePort(port=50051, target_port=50051),
                        client.V1ServicePort(port=5000, target_port=5000)
                    ]
                )
            )

            self.core_api.create_namespaced_service(
                namespace=self.namespace, body=service)
            logging.info(f"Service {service_name} created.")

            self.create_ambassador_mappings()
        except ApiException as e:
            logging.error(f"Failed to create service: {e}")

    def create_ambassador_mappings(self):
        try:
            mappings = [
                {
                    "apiVersion": "getambassador.io/v2",
                    "kind": "Mapping",
                    "metadata": {"name": f"{self.deployment_name}-infer", "namespace": self.namespace},
                    "spec": {
                        "prefix": f"/{self.deployment_name}/infer",
                        "service": f"{self.deployment_name}-svc.vdags.svc.cluster.local:50051"
                    }
                },
                {
                    "apiVersion": "getambassador.io/v2",
                    "kind": "Mapping",
                    "metadata": {"name": f"{self.deployment_name}-config", "namespace": self.namespace},
                    "spec": {
                        "prefix": f"/{self.deployment_name}/config",
                        "service": f"{self.deployment_name}-svc.vdags.svc.cluster.local:5000"
                    }
                }
            ]

            for mapping in mappings:
                self.custom_api.create_namespaced_custom_object(
                    group="getambassador.io",
                    version="v2",
                    namespace=self.namespace,
                    plural="mappings",
                    body=mapping
                )
                logging.info(
                    f"Ambassador mapping {mapping['metadata']['name']} created.")
        except ApiException as e:
            logging.error(f"Failed to create ambassador mappings: {e}")

    def delete_deployment(self):
        try:
            self.api.delete_namespaced_deployment(
                name=self.deployment_name, namespace=self.namespace)
            logging.info(f"Deployment {self.deployment_name} deleted.")
        except ApiException as e:
            logging.error(f"Failed to delete deployment: {e}")

    def delete_service(self):
        try:
            service_name = f"{self.deployment_name}-svc"
            self.core_api.delete_namespaced_service(
                name=service_name, namespace=self.namespace)
            logging.info(f"Service {service_name} deleted.")
        except ApiException as e:
            logging.error(f"Failed to delete service: {e}")

    def set_scale(self, replicas: int):
        try:
            scale = self.api.read_namespaced_deployment_scale(
                name=self.deployment_name, namespace=self.namespace)
            scale.spec.replicas = replicas
            self.api.patch_namespaced_deployment_scale(
                name=self.deployment_name, namespace=self.namespace, body=scale)
            logging.info(
                f"Scaled {self.deployment_name} to {replicas} replicas.")
        except ApiException as e:
            logging.error(f"Failed to scale deployment: {e}")

    def list_deployments(self):
        try:
            deployments = self.api.list_namespaced_deployment(
                namespace=self.namespace)
            deployment_names = [
                deployment.metadata.name for deployment in deployments.items]
            logging.info(
                f"Deployments in namespace '{self.namespace}': {deployment_names}")
            return deployment_names
        except ApiException as e:
            logging.error(f"Failed to list deployments: {e}")
            return []
