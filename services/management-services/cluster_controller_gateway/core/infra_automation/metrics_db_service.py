import os
import time
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

class MetricsWriterManager:
    def __init__(
        self,
        kube_config_data: str,
        redis_host_block_metrics: str,
        cluster_id: str,
        redis_host_cluster_metrics: str,
        write_interval: str,
        mongo_service_url: str,
        globals={},
        cluster_data={}
    ):
        logger.info("Initializing MetricsWriterManager...")
        config.load_kube_config_from_dict(kube_config_data)
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = "metrics"
        self.deployment_name = "metrics-writer"
        self.service_name = "metrics-writer-svc"
        self.redis_container_name = "metrics-redis"
        self.redis_port = 6379
        self.redis_image = "redis:latest"
        self.redis_env_vars = []
        self.redis_service_port = 6379
        self.redis_container_port = 6379
        self.redis_host_block_metrics = redis_host_block_metrics
        self.cluster_id = cluster_id
        self.redis_host_cluster_metrics = redis_host_cluster_metrics
        self.write_interval = write_interval
        self.mongo_service_url = mongo_service_url
        self.globals = globals
        self.cluster_data = cluster_data

        logger.info(f"cluster data: {self.cluster_data}")

    def get_metrics_collect_interval(self):
        try:
            logger.info("Retrieving cluster metrics collect interval...")
            cfg = self.cluster_data['config']
            interval = str(cfg.get("clusterMetricsCollectInterval", 30))
            logger.info(f"Collect interval set to: {interval}")
            return interval
        except Exception as e:
            logger.exception("Failed to retrieve metrics collect interval")
            raise

    def create(self):
        try:
            logger.info("Creating Metrics Writer Deployment and Service...")

            metrics_collect_interval = self.get_metrics_collect_interval()

            global_block_metrics_redis_host = self.globals['global_block_metrics_redis_host']
            global_cluster_metrics_redis_host = self.globals['global_cluster_metrics_redis_host']
            global_vdag_metrics_redis_host = self.globals['global_vdag_metrics_redis_host']

            logger.info("Constructing Deployment spec...")
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
                                    name="metrics-writer",
                                    image_pull_policy="Always",
                                    image=os.getenv("METRICS_WRITER_SERVICE_IMAGE_NAME"),
                                    env=[
                                        client.V1EnvVar(
                                            name="BLOCK_METRICS_GLOBAL_DB_REDIS_HOST", value=global_block_metrics_redis_host),
                                        client.V1EnvVar(
                                            name="CLUSTER_ID", value=self.cluster_id),
                                        client.V1EnvVar(
                                            name="CLUSTER_METRICS_GLOBAL_DB_REDIS_HOST", value=global_cluster_metrics_redis_host),
                                        client.V1EnvVar(
                                            name="VDAG_METRICS_GLOBAL_DB_REDIS_HOST", value=global_vdag_metrics_redis_host),
                                        client.V1EnvVar(
                                            name="CLUSTER_METRICS_WRITE_INTERVAL", value=metrics_collect_interval),
                                        client.V1EnvVar(
                                            name="MONGO_URL", value=self.mongo_service_url),
                                    ],
                                    ports=[client.V1ContainerPort(container_port=5000)]
                                ),
                                client.V1Container(
                                    name=self.redis_container_name,
                                    image=self.redis_image,
                                    ports=[client.V1ContainerPort(container_port=self.redis_container_port)]
                                )
                            ]
                        )
                    )
                )
            )

            logger.info("Creating deployment in namespace 'metrics'...")
            self.apps_v1.create_namespaced_deployment(namespace=self.namespace, body=deployment)
            logger.info("Deployment created successfully.")

            logger.info("Constructing Service spec...")
            service_spec = client.V1ServiceSpec(
                
                selector={"app": self.deployment_name},
                ports=[
                    client.V1ServicePort(name="api", port=5000, target_port=5000),
                    client.V1ServicePort(name="redis", port=self.redis_service_port, target_port=self.redis_container_port)
                ]
            )

            if self.cluster_data.get('config', {}).get('useGateway', False):
                logger.info("Gateway enabled, using Ambassador Mapping.")
                service_spec.annotations = {
                    "getambassador.io/config": (
                        "---\napiVersion: ambassador/v1\nkind: Mapping\n"
                        "name: metrics-writer-mapping\nprefix: /metrics\n"
                        "service: metrics-writer-svc.metrics.svc.cluster.local:5000"
                    )
                }
                service_spec.type = "ClusterIP"
            else:
                logger.info("Gateway not used, assigning NodePort 32301.")
                service_spec.type = "NodePort"
                service_spec.ports[0].node_port = 32301

            service = client.V1Service(
                metadata=client.V1ObjectMeta(name=self.service_name),
                spec=service_spec
            )

            logger.info("Creating service in namespace 'metrics'...")
            self.core_v1.create_namespaced_service(namespace=self.namespace, body=service)
            logger.info("Service created successfully.")

            logger.info("Waiting for deployment to become ready...")
            self._wait_for_deployment()
            logger.info("Metrics Writer is ready.")
        except ApiException as e:
            logger.exception("Kubernetes API error occurred")
            raise RuntimeError(f"Kubernetes API error: {e}")
        except Exception as e:
            logger.exception("Unexpected error occurred during creation")
            raise RuntimeError(f"Unexpected error during creation: {e}")

    def remove(self):
        try:
            logger.info("Removing Metrics Writer deployment and service...")
            self.apps_v1.delete_namespaced_deployment(
                name=self.deployment_name, namespace=self.namespace)
            self.core_v1.delete_namespaced_service(
                name=self.service_name, namespace=self.namespace)
            logger.info("Removal completed successfully.")
        except ApiException as e:
            logger.exception("Kubernetes API error occurred during removal")
            raise RuntimeError(f"Kubernetes API error: {e}")
        except Exception as e:
            logger.exception("Unexpected error occurred during removal")
            raise RuntimeError(f"Unexpected error during removal: {e}")

    def _wait_for_deployment(self, timeout=300):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=self.deployment_name, namespace=self.namespace)
                if deployment.status.available_replicas == deployment.spec.replicas:
                    logger.info("Deployment is now available.")
                    return
            except Exception as e:
                logger.warning(f"Error while checking deployment status: {e}")
            time.sleep(2)
        logger.error(f"Timeout while waiting for deployment '{self.deployment_name}' to become ready.")
        raise TimeoutError(
            f"Deployment '{self.deployment_name}' did not become ready within {timeout} seconds.")
