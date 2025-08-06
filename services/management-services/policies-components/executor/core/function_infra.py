from kubernetes import client, config
from kubernetes.client.rest import ApiException
import json
import os


class PolicyFunctionInfra:
    def __init__(self):
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        self.apps_api = client.AppsV1Api()
        self.core_api = client.CoreV1Api()
        self.autoscaling_api = client.AutoscalingV2Api()

        self.namespace = "policies"

        # Ensure the namespace exists
        self._ensure_namespace()

    def _ensure_namespace(self):
        try:
            self.core_api.read_namespace(name=self.namespace)
        except ApiException as e:
            if e.status == 404:
                namespace_body = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=self.namespace))
                self.core_api.create_namespace(namespace_body)
            else:
                raise

    def create_deployment(self, name, policy_rule_uri, policy_rule_parameters=None, replicas=1, autoscaling=None, node_selector=None):

        try:
            # Deployment spec
            container_env = [
                client.V1EnvVar(name="POLICY_RULE_URI", value=policy_rule_uri),
                client.V1EnvVar(name="POLICY_DB_URL", value=os.getenv("POLICY_DB_URL"))
            ]

            if policy_rule_parameters:
                container_env.append(
                    client.V1EnvVar(name="POLICY_RULE_PARAMETERS",
                                    value=json.dumps(policy_rule_parameters))
                )

            container = client.V1Container(
                name=name,
                image=os.getenv("DEFAULT_POLICY_CONTAINER_IMAGE"),
                ports=[client.V1ContainerPort(container_port=5000)],
                env=container_env
            )

            pod_spec = client.V1PodSpec(containers=[container])

            if node_selector:
                pod_spec.node_selector = node_selector

            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": name}),
                spec=pod_spec
            )

            spec = client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels={"app": name}),
                template=template
            )

            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(name=name, namespace=self.namespace),
                spec=spec
            )

            self.apps_api.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)

            if autoscaling:
                self._create_autoscaler(name, autoscaling)

            # Create service for the deployment
            self.create_service(name)

            print(f"Deployment '{name}' created successfully.")

        except Exception as e:
            raise Exception(f"Error creating deployment: {e}")

    def _create_autoscaler(self, name, autoscaling):
        hpa_spec = client.V2HorizontalPodAutoscalerSpec(
            scale_target_ref=client.V2CrossVersionObjectReference(
                api_version="apps/v1",
                kind="Deployment",
                name=name
            ),
            min_replicas=autoscaling["min_replicas"],
            max_replicas=autoscaling["max_replicas"],
            metrics=[
                client.V2MetricSpec(
                    type="Resource",
                    resource=client.V2ResourceMetricSource(
                        name="cpu",
                        target=client.V2MetricTarget(
                            type="Utilization",
                            average_utilization=autoscaling["target_cpu_utilization_percentage"]
                        )
                    )
                )
            ]
        )

        hpa = client.V2HorizontalPodAutoscaler(
            api_version="autoscaling/v2",
            kind="HorizontalPodAutoscaler",
            metadata=client.V1ObjectMeta(name=name, namespace=self.namespace),
            spec=hpa_spec
        )

        try:
            self.autoscaling_api.create_namespaced_horizontal_pod_autoscaler(
                namespace=self.namespace, body=hpa
            )
            print(f"Autoscaler for deployment '{name}' created successfully.")
        except ApiException as e:
            raise Exception(f"Error creating autoscaler: {e}")

    def create_service(self, name):

        service_spec = client.V1ServiceSpec(
            selector={"app": name},
            ports=[client.V1ServicePort(
                protocol="TCP", port=5000, target_port=5000, name="rest")],
            type="ClusterIP"
        )

        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=f"{name}-svc", namespace=self.namespace),
            spec=service_spec
        )

        try:
            self.core_api.create_namespaced_service(
                namespace=self.namespace, body=service)
            print(f"Service '{name}-svc' created successfully.")
        except ApiException as e:
            if e.status == 409:
                print(f"Service '{name}-svc' already exists.")
            else:
                raise Exception(f"Error creating service: {e}")

    def remove_deployment(self, name):

        try:
            # Delete the autoscaler if it exists
            try:
                self.autoscaling_api.delete_namespaced_horizontal_pod_autoscaler(
                    name=name, namespace=self.namespace
                )
                print(
                    f"Autoscaler for deployment '{name}' deleted successfully.")
            except ApiException as e:
                if e.status != 404:
                    raise

            # Delete the deployment
            self.apps_api.delete_namespaced_deployment(
                name=name, namespace=self.namespace)
            print(f"Deployment '{name}' deleted successfully.")

            # Delete the service
            try:
                self.core_api.delete_namespaced_service(
                    name=f"{name}-svc", namespace=self.namespace)
                print(f"Service '{name}-svc' deleted successfully.")
            except ApiException as e:
                if e.status != 404:
                    raise

        except ApiException as e:
            raise Exception(f"Error removing deployment: {e}")
    

    def get_logs(self, name, tail=None):
       
        try:
            pod_list = self.core_api.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"app={name}"
            )
            if not pod_list.items:
                return f"No pods found for deployment '{name}'."

            logs_output = []
            for pod in pod_list.items:
                pod_name = pod.metadata.name
                try:
                    log = self.core_api.read_namespaced_pod_log(
                        name=pod_name,
                        namespace=self.namespace,
                        tail_lines=tail
                    )
                    logs_output.append(f"--- Logs from pod {pod_name} ---\n{log}")
                except ApiException as e:
                    logs_output.append(f"Error fetching logs from pod {pod_name}: {e}")

            return "\n\n".join(logs_output)

        except Exception as e:
            raise Exception(f"Error getting logs for deployment '{name}': {e}")
