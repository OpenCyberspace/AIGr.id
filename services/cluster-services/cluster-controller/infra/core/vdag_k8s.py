import os
import logging
import json
import random
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logging.basicConfig(level=logging.INFO)


class vDAGInfraManager:
    def __init__(self, deployment_name: str, vdag_uri: str, policy_execution_mode: str):
        self.deployment_name = deployment_name
        self.namespace = "vdags"
        self.image = os.getenv("VDAG_CONTROLLER_IMAGE_NAME",
                               "34.58.1.86:31280/block/vdag-controller")

        if self.image == "":
            self.image = "34.58.1.86:31280/block/vdag-controller"

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

        self.api = client.AppsV1Api()
        self.core_api = client.CoreV1Api()
        self.custom_api = client.CustomObjectsApi()
        self.inference_server = ""
        self.policy_execution_mode = policy_execution_mode
        self.vdag_uri = vdag_uri
        self.enable_redis = False

        self.ensure_namespace()

    def ensure_namespace(self):
        try:
            self.core_api.read_namespace(name=self.namespace)
        except ApiException as e:
            if e.status == 404:
                ns_body = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=self.namespace))
                self.core_api.create_namespace(body=ns_body)
                logging.info(f"Namespace '{self.namespace}' created.")
            else:
                logging.error(f"Failed to check/create namespace: {e}")

    def create_controller(self, replicas=1, custom_data=None, autoscaler_config=None):
        self.create_deployment(replicas, custom_data, autoscaler_config)
        return self.create_service()

    def remove_controller(self):
        self.delete_service()
        self.delete_deployment()

    def create_deployment(self, replicas=1, custom_data=None, autoscaler_config=None):
        try:
            env_vars = [
                client.V1EnvVar(name="VDAG_URI", value=self.vdag_uri),
                client.V1EnvVar(
                    name="VDAG_ADHOC_INFERENCE_SERVER_URL", value=self.inference_server),
                client.V1EnvVar(name="VDAG_DB_API_URL",
                                value=os.getenv("VDAG_DB_API_URL", "")),
                client.V1EnvVar(name="POLICY_SYSTEM_EXECUTOR_ID", value=os.getenv(
                    "CLUSTER_DEFAULT_POLICY_EXECUTOR", "")),
                client.V1EnvVar(name="POLICY_EXECUTION_MODE",
                                value=self.policy_execution_mode),
                client.V1EnvVar(name="POLICY_DB_URL",
                                value=os.getenv("POLICY_DB_URL", "")),
                client.V1EnvVar(name="BLOCKS_DB_URL",
                                value=os.getenv("BLOCKS_SERVICE_URL", "")),
                client.V1EnvVar(name="METRICS_REDIS_HOST",
                                value=os.getenv("METRICS_REDIS_HOST", "")),
                client.V1EnvVar(name="DEPLOYMENT_NAME",
                                value=self.deployment_name)
            ]

            if custom_data:
                env_vars.append(client.V1EnvVar(
                    name="VDAG_CUSTOM_INIT_DATA", value=json.dumps(custom_data)
                ))

            # Main container
            container = client.V1Container(
                name=self.deployment_name,
                image=self.image,
                image_pull_policy="Always",
                ports=[
                    client.V1ContainerPort(container_port=50051, name="rpc"),
                    client.V1ContainerPort(container_port=5000, name="rest"),
                    client.V1ContainerPort(container_port=50052, name="api")
                ],
                env=env_vars
            )

            containers = [container, client.V1Container(
                name="redis",
                image="redis",
                image_pull_policy="Always",
                ports=[client.V1ContainerPort(container_port=6379)]
            )]

            # Pod template
            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": self.deployment_name}),
                spec=client.V1PodSpec(containers=containers)
            )

            # Deployment spec
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

            # Create Deployment
            self.api.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)
            logging.info(f"Deployment {self.deployment_name} created.")

            # Optional autoscaler
            if autoscaler_config:
                hpa = client.V2HorizontalPodAutoscaler(
                    metadata=client.V1ObjectMeta(
                        name=self.deployment_name, namespace=self.namespace),
                    spec=client.V2HorizontalPodAutoscalerSpec(
                        scale_target_ref=client.V2CrossVersionObjectReference(
                            api_version="apps/v1",
                            kind="Deployment",
                            name=self.deployment_name
                        ),
                        min_replicas=autoscaler_config.get("min_replicas", 1),
                        max_replicas=autoscaler_config.get("max_replicas", 10),
                        metrics=[
                            client.V2MetricSpec(
                                type="Resource",
                                resource=client.V2ResourceMetricSource(
                                    name="cpu",
                                    target=client.V2MetricTarget(
                                        type="Utilization",
                                        average_utilization=autoscaler_config.get(
                                            "target_cpu_utilization_percentage", 70)
                                    )
                                )
                            )
                        ]
                    )
                )

                autoscaling_api = client.AutoscalingV2Api()
                autoscaling_api.create_namespaced_horizontal_pod_autoscaler(
                    namespace=self.namespace, body=hpa)
                logging.info(f"HPA for {self.deployment_name} created.")

        except Exception as e:
            logging.error(f"Failed to create deployment or autoscaler: {e}")

    def create_service(self):
        service_name = f"{self.deployment_name}-svc"
        try:
            service = client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=service_name, namespace=self.namespace),
                spec=client.V1ServiceSpec(
                    type="NodePort",
                    selector={"app": self.deployment_name},
                    ports=[
                        client.V1ServicePort(
                            port=50051, target_port=50051, name="rpc"),
                        client.V1ServicePort(
                            port=50052, target_port=50052, name="api"),
                        client.V1ServicePort(
                            port=5000, target_port=5000, name="rest")
                    ]
                )
            )

            created_service = self.core_api.create_namespaced_service(
                namespace=self.namespace, body=service)
            logging.info(f"Service {service_name} created.")

            grpc_port = None
            http_port = None
            api_port = None

            for p in created_service.spec.ports:
                if p.port == 50051:
                    grpc_port = p.node_port
                elif p.port == 5000:
                    http_port = p.node_port
                elif p.port == 50052:
                    api_port = p.node_port

            logging.info(
                f"Assigned NodePorts - gRPC: {grpc_port}, HTTP: {http_port}")
            return {
                "grpc": grpc_port,
                "http": http_port,
                "api": api_port
            }

        except ApiException as e:
            logging.error(f"Failed to create service: {e}")
            return {
                "grpc": None,
                "http": None
            }

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
            return [d.metadata.name for d in deployments.items]
        except ApiException as e:
            logging.error(f"Failed to list deployments: {e}")
            return []

    def discover_inference_servers(self):
        try:
            inference_namespace = "inference-server"
            services = self.core_api.list_namespaced_service(
                namespace=inference_namespace)
            valid_services = [s.metadata.name for s in services.items if s.spec.ports and any(
                p.port == 50052 for p in s.spec.ports)]

            if not valid_services:
                logging.warning("No inference servers found.")
                return None

            selected = random.choice(valid_services)
            url = f"{selected}.{inference_namespace}.svc.cluster.local:50052"
            logging.info(f"Discovered inference server: {url}")
            return url
        except ApiException as e:
            logging.error(f"Failed to discover inference servers: {e}")
            return None
