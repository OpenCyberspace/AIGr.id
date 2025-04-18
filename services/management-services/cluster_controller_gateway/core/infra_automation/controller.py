from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time
import json


class ClusterControllerInfra:
    def __init__(self, kube_config_data: str, cluster_id: str, env_vars: dict, cluster_data: dict, globals={}):
        config.load_kube_config_from_dict(kube_config_data)
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = "controllers"
        self.deployment_name = f"{cluster_id}-controller"
        self.service_name = f"{cluster_id}-controller-svc"
        self.cluster_id = cluster_id
        self.env_vars = env_vars
        self.cluster_data = cluster_data
        self.globals = globals

    def parse_cluster_policy_config(self):
        try:
            if not hasattr(self, 'cluster_data') or not isinstance(self.cluster_data, dict):
                raise ValueError(
                    "Invalid or missing 'cluster_data' attribute.")

            cluster_data = self.cluster_data

            if 'config' not in cluster_data or not isinstance(cluster_data['config'], dict):
                raise ValueError(
                    "Missing or invalid 'config' key in 'cluster_data'.")

            config = cluster_data['config']

            # parse policy data:
            policy_executor_id = config.get('policyExecutorId', '')
            policy_execution_mode = config.get('policyExecutionMode', 'local')

            custom_policy_system = config.get('customPolicySystem', None)

            return policy_executor_id, policy_execution_mode, custom_policy_system
        except Exception as e:
            raise e

    def prepare_url_map(self):
        try:
            cluster_data = self.cluster_data
            config = cluster_data['config']
            public_host = config['publicHostname']
            # Default to True if not provided
            use_gateway = config.get('useGateway', True)

            if use_gateway:
                cluster_svc_url = f"http://{public_host}:32000/controller"
                cluster_metrics_url = f"http://{public_host}:32000/metrics"
                blocks_tx_service_url = f"http://{public_host}:32000/blocks"
                public_controller_gateway = f"http://{public_host}:32000"
                parameter_update_url = f"http://{public_host}:32000/mgmt"
            else:
                cluster_svc_url = f"http://{public_host}:32300"
                cluster_metrics_url = f"http://{public_host}:32301"
                blocks_tx_service_url = f"http://{public_host}:32302"
                public_controller_gateway = f"http://{public_host}:32000",
                parameter_update_url = f"http://{public_host}:32303"

            return {
                "controllerService": cluster_svc_url,
                "metricsService": cluster_metrics_url,
                "blocksQuery": blocks_tx_service_url,
                "publicGateway": public_controller_gateway,
                "parameterUpdater": parameter_update_url
            }

        except Exception as e:
            raise e

    def get_cluster_actions_map(self):
        try:
            if not hasattr(self, 'cluster_data') or not isinstance(self.cluster_data, dict):
                raise ValueError(
                    "Invalid or missing 'cluster_data' attribute.")

            cluster_data = self.cluster_data

            if 'config' not in cluster_data or not isinstance(cluster_data['config'], dict):
                raise ValueError(
                    "Missing or invalid 'config' key in 'cluster_data'.")

            config = cluster_data['config']

            return config.get('actionsPolicyMap', {})

        except Exception as e:
            raise e

    def is_ingress(self):
        try:
            if not hasattr(self, 'cluster_data') or not isinstance(self.cluster_data, dict):
                raise ValueError(
                    "Invalid or missing 'cluster_data' attribute.")

            cluster_data = self.cluster_data

            if 'config' not in cluster_data or not isinstance(cluster_data['config'], dict):
                raise ValueError(
                    "Missing or invalid 'config' key in 'cluster_data'.")

            config = cluster_data['config']

            use_gateway = config.get('useGateway', True)
            return use_gateway

        except Exception as e:
            raise e

    def create(self):
        try:
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
                                self._create_container(
                                    "redis", "redis:latest", []),
                                self._create_container(
                                    "infra", "aiosv1/infra:v1", self._infra_env_vars(),
                                    ports=[4000]
                                ),
                                self._create_container(
                                    "block-transactions", "aiosv1/block-transactions:v1",
                                    self._block_transactions_env_vars(),
                                    ports=[8000]
                                ),
                                self._create_container(
                                    "parameter-updater", "aiosv1/dyn:v1",
                                    self._block_transactions_env_vars(),
                                    ports=[8000]
                                )
                            ]
                        )
                    )
                )
            )
            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)
            self._create_service()
            self._wait_for_deployment()
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

    def _wait_for_deployment(self, timeout=300):
        start_time = time.time()
        while time.time() - start_time < timeout:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=self.deployment_name, namespace=self.namespace)
            if deployment.status.ready_replicas == deployment.status.replicas:
                return
            time.sleep(2)
        raise TimeoutError(
            f"Deployment '{self.deployment_name}' did not become ready within {timeout} seconds.")

    def _create_service(self):
        is_ingress = self.is_ingress()

        service_ports = []

        if is_ingress:
            annotations = {
                "getambassador.io/config": f"""
    ---
    apiVersion: getambassador.io/v2
    kind: Mapping
    metadata:
    name: infra-mapping
    spec:
    prefix: /controller
    service: http://{self.service_name}:4000
    ---
    apiVersion: getambassador.io/v2
    kind: Mapping
    metadata:
    name: block-transactions-mapping
    spec:
    prefix: /blocks
    service: http://{self.service_name}.controllers.svc.cluster.local:8000
    ---
    apiVersion: getambassador.io/v2
    kind: Mapping
    metadata:
    name: mgmt
    spec:
    prefix: /mgmt
    service: http://{self.service_name}.controllers.svc.cluster.local:10000
    """
            }
        else:
            annotations = {}
            service_ports.extend([
                client.V1ServicePort(
                    port=4000, target_port=4000, node_port=32300),
                client.V1ServicePort(
                    port=8000, target_port=8000, node_port=32302),
                client.V1ServicePort(
                    port=10000, target_port=10000, node_port=32303)
            ])

        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=self.service_name, annotations=annotations),
            spec=client.V1ServiceSpec(
                selector={"app": self.deployment_name},
                ports=service_ports,
                type="NodePort"
            )
        )
        self.core_v1.create_namespaced_service(
            namespace=self.namespace, body=service)

    def _create_container(self, name, image, env_vars, ports=None):
        return client.V1Container(
            name=name,
            image=image,
            env=env_vars,
            ports=[client.V1ContainerPort(container_port=p)
                   for p in ports] if ports else None
        )

    def _infra_env_vars(self):

        policy_executor_id, policy_execution_mode = self.parse_cluster_policy_config()
        policy_db_service_url = self.globals['policy_db_url']
        blocks_db_url = self.globals['blocks_db_url']
        cluster_db_url = self.globals['cluster_db_url']
        vdag_controller_image_name = self.globals['vdag_controller_image_name']
        vdag_adhoc_inference_service_url = self.globals['vdag_adhoc_inference_server_url']
        vdag_db_url = self.globals['vdag_db_url']
        vdag_controller_db_url = self.globals['vdag_controller_db_url']

        cluster_actions = self.get_cluster_actions_map()

        return [
            client.V1EnvVar(name="CLUSTER_ID", value=self.cluster_id),
            client.V1EnvVar(name="METRICS_SERVICE_URL",
                            value="http://metrics-writer-svc.metrics.svc.cluster.local:5000"),
            client.V1EnvVar(name="POLICY_SYSTEM_EXECUTOR_ID",
                            value=policy_executor_id),
            client.V1EnvVar(name="CLUSTER_SERVICE_URL", value=cluster_db_url),
            client.V1EnvVar(name="BLOCKS_SERVICE_URL", value=blocks_db_url),
            client.V1EnvVar(name="VDAG_CONTROLLER_DB_URL",
                            value=vdag_controller_db_url),
            client.V1EnvVar(name="METRICS_REDIS_HOST",
                            value="metrics-writer-svc.metrics.svc.cluster.local"),
            client.V1EnvVar(name="VDAG_CONTROLLER_IMAGE_NAME",
                            value=vdag_controller_image_name),
            client.V1EnvVar(name="VDAG_ADHOC_INFERENCE_SERVER_URL",
                            value=vdag_adhoc_inference_service_url),
            client.V1EnvVar(name="CLUSTER_ACTIONS_MAP",
                            value=json.dumps(cluster_actions)),
            client.V1EnvVar(name="CLUSTER_DEFAULT_POLICY_EXECUTOR",
                            value=policy_executor_id),
            client.V1EnvVar(name="POLICY_EXECUTION_MODE",
                            value=policy_execution_mode),
            client.V1EnvVar(name="POLICY_DB_URL", value=policy_db_service_url),
            client.V1EnvVar(name="VDAG_DB_API_URL", value=vdag_db_url),
            client.V1EnvVar(name="REDIS_URL",
                            value=self.env_vars.get("REDIS_URL", "")),
            client.V1EnvVar(name="POLICY_RULE_REMOTE_URL",
                            value=policy_db_service_url),
            client.V1EnvVar(name="POLICY_EXECUTOR_HOST_URL",
                            value=policy_db_service_url),
            client.V1EnvVar(name="CLUSTER_DRY_RUN_MODE",
                            value=self.env_vars.get("CLUSTER_DRY_RUN_MODE", "")),
            client.V1EnvVar(name="CLUSTER_METRICS_SERVICE_URL",
                            value="http://metrics-writer-svc.metrics.svc.cluster.local:5000"),
        ]

    def _block_transactions_env_vars(self):

        blocks_db_url = self.globals['blocks_db_url']
        cluster_db_url = self.globals['cluster_db_url']

        return [
            client.V1EnvVar(name="BLOCKS_SERVICE_URL", value=blocks_db_url),
            client.V1EnvVar(name="CLUSTER_ID", value=self.cluster_id),
            client.V1EnvVar(name="CLUSTER_SERVICE_URL", value=cluster_db_url),
        ]
