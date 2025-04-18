import logging
import os
from kubernetes import client, config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_namespace_exists(namespace):
    core_v1 = client.CoreV1Api()
    try:
        core_v1.read_namespace(name=namespace)
        logger.info(f"Namespace '{namespace}' already exists.")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            namespace_body = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=namespace)
            )
            core_v1.create_namespace(body=namespace_body)
            logger.info(f"Namespace '{namespace}' created.")
        else:
            logger.error(
                f"Failed to verify or create namespace '{namespace}': {e}")
            raise


def add_env_vars_to_containers(deployment, block_id):
    env_vars = {}

    # Common env var for all containers
    kubernetes_node_name_env = client.V1EnvVar(
        name="KUBERNETES_NODE_NAME",
        value_from=client.V1EnvVarSource(
            field_ref=client.V1ObjectFieldSelector(
                api_version="v1", field_path="spec.nodeName"
            )
        )
    )

    # export globals:

    # export locals:
    local_params = {

    }

    # mapping container:
    env_vars["mapping"] = [
        client.V1EnvVar(name="BLOCK_ID", value=block_id),
        client.V1EnvVar(name="CLUSTER_PROMETHEUS_URL",
                        value=os.getenv("CLUSTER_PROMETHEUS_URL", ""))
    ]

    env_vars["block-executor"] = [
        client.V1EnvVar(name="BLOCK_ID", value=block_id),
        client.V1EnvVar(name="BLOCKS_DB_URI",
                        value=os.getenv("BLOCKS_SERVICE_URL", "")),
        client.V1EnvVar(name="POLICY_DB_URL",
                        value=os.getenv("POLICY_DB_URL", "")),
        client.V1EnvVar(name="CLUSTER_METRICS_SERVICE_URL",
                        value=os.getenv("CLUSTER_METRICS_SERVICE_URL", "")),
        client.V1EnvVar(name="METRICS_REDIS_HOST",
                        value=os.getenv("METRICS_REDIS_HOST", "")),
        client.V1EnvVar(name="VDAG_DB_API_URL",
                        value=os.getenv("VDAG_DB_API_URL", "")),
        client.V1EnvVar(name="CLUSTER_ID", value=os.getenv("CLUSTER_ID")),
    ]

    cluster_id = os.getenv("CLUSTER_ID", "")

    env_vars["autoscaler"] = [
        client.V1EnvVar(name="BLOCK_ID", value=block_id),
        client.V1EnvVar(name="CLUSTER_ID", value=cluster_id),
        client.V1EnvVar(name="BLOCKS_SERVICE_URL",
                        value=os.getenv("BLOCKS_SERVICE_URL", "")),
        client.V1EnvVar(name="CLUSTER_SERVICE_URL",
                        value=os.getenv("CLUSTER_SERVICE_URL", "")),
        client.V1EnvVar(name="POLICY_DB_URL",
                        value=os.getenv("POLICY_DB_URL", "")),
        client.V1EnvVar(name="CLUSTER_METRICS_SERVICE_URL",
                        value=os.getenv("CLUSTER_METRICS_SERVICE_URL", "")),
        client.V1EnvVar(name="CONTROLLER_URL",
                        value=f"http://{cluster_id}-controller-svc.controllers.svc.cluster.local:4000" if cluster_id else "")
    ]

    if not deployment.spec.template.spec.containers:
        raise ValueError("Deployment has no containers defined.")

    for container in deployment.spec.template.spec.containers:
        container.env = (container.env or []) + \
            env_vars.get(container.name, [])
        # Add KUBERNETES_NODE_NAME
        container.env.append(kubernetes_node_name_env)

    return deployment


def add_instance_env_variables(deployment, block_id, instance_id, gpus=[]):
    if not deployment.spec.template.spec.containers:
        raise ValueError("Deployment has no containers defined.")

    try:
        kubernetes_node_name_env = client.V1EnvVar(
            name="KUBERNETES_NODE_NAME",
            value_from=client.V1EnvVarSource(
                field_ref=client.V1ObjectFieldSelector(
                    api_version="v1", field_path="spec.nodeName"
                )
            )
        )

        envs = [
            client.V1EnvVar(name="INSTANCE_ID", value=instance_id),
            client.V1EnvVar(name="BLOCK_ID", value=block_id),
            client.V1EnvVar(name="BLOCKS_DB_URI",
                            value=os.getenv("BLOCKS_SERVICE_URL", "")),
            client.V1EnvVar(name="METRICS_REDIS_HOST",
                            value=os.getenv("METRICS_REDIS_HOST", "")),
            client.V1EnvVar(name="POLICY_DB_URL",
                            value=os.getenv("POLICY_DB_URL", "")),
            client.V1EnvVar(name="VDAG_DB_API_URL",
                            value=os.getenv("VDAG_DB_API_URL", ""))
        ]

        if gpus:
            gpu_ids = ",".join(map(str, gpus))
            envs.append(client.V1EnvVar(
                name="NVIDIA_VISIBLE_DEVICES", value=gpu_ids))
            envs.append(client.V1EnvVar(
                name="NVIDIA_DRIVER_CAPABILITIES", value="all"))

        for container in deployment.spec.template.spec.containers:
            container.env = (container.env or []) + envs
            # Add KUBERNETES_NODE_NAME
            container.env.append(kubernetes_node_name_env)

        return deployment

    except Exception as e:
        raise RuntimeError(
            f"Failed to add instance environment variables: {str(e)}") from e


def create_executor(block_id, namespace="blocks"):
    try:
        # Load kube config
        config.load_kube_config()

        ensure_namespace_exists(namespace)

        deployment_name = f"{block_id}-executor"

        # Create a V1Deployment object
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=deployment_name, labels={"blockID": block_id, "instanceID": "executor"}),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"app": deployment_name}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": deployment_name, "blockID": block_id, "instanceID": "executor"}),
                    spec=client.V1PodSpec(containers=[
                        client.V1Container(
                            name="redis",
                            image="bitnami/redis",
                            ports=[client.V1ContainerPort(container_port=6379)]
                        ),
                        client.V1Container(
                            name="block-executor",
                            image="aiosv1/block_executor:v1",
                            ports=[
                                client.V1ContainerPort(container_port=18000),
                                client.V1ContainerPort(container_port=18001)
                            ],
                            env=[]
                        ),
                        client.V1Container(
                            name="mapping",
                            image="aiosv1/block_mapping:v1",
                            ports=[client.V1ContainerPort(container_port=5000)]
                        ),
                        client.V1Container(
                            name="autoscaler",
                            image="aiosv1/autoscaler:v1",
                            ports=[
                                client.V1ContainerPort(container_port=10000)
                            ],
                            env=[]
                        ),
                        client.V1Container(
                            name="proxy",
                            image="aiov1/executor_proxy:v1",
                            ports=[
                                client.V1ContainerPort(container_port=50051)
                            ],
                            env=[]
                        ),
                        client.V1Container(
                            name="health",
                            image="aiov1/health_checker:v1",
                            ports=[
                                client.V1ContainerPort(container_port=19001)
                            ],
                            env=[]
                        )
                    ])
                )
            )
        )

        deployment = add_env_vars_to_containers(deployment, block_id)

        # Create the deployment
        apps_v1 = client.AppsV1Api()
        apps_v1.create_namespaced_deployment(
            namespace=namespace, body=deployment)

        # Create a service
        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(name=f"{deployment_name}-svc"),
            spec=client.V1ServiceSpec(
                selector={"app": deployment_name},
                ports=[
                    client.V1ServicePort(
                        port=6379, target_port=6379, name="redis"),
                    client.V1ServicePort(
                        port=50051, target_port=50051, name="grpc"),
                    client.V1ServicePort(
                        port=18000, target_port=18000, name="metrics"),
                    client.V1ServicePort(
                        port=18001, target_port=18001, name="control"),
                    client.V1ServicePort(
                        port=5000, target_port=5000, name="mapping"),
                    client.V1ServicePort(
                        port=10000, target_port=10000, name="scaler"
                    ),
                    client.V1ServicePort(
                        port=19001, target_port=19001, name="health"
                    )
                ]
            )
        )

        # Create the service
        core_v1 = client.CoreV1Api()
        core_v1.create_namespaced_service(namespace=namespace, body=service)

        logger.info(
            f"Deployment and Service for {deployment_name} created successfully.")
    except Exception as e:
        logger.error("failed to create k8s deployment: f{e}")
        raise e


def create_single_instance(block_id, instance_id, container_image, node_tag="none", namespace="blocks", gpus=[]):
    try:
        # Load kube config
        config.load_kube_config()

        deployment_name = f"{block_id}-{instance_id}"
        service_name = f"{deployment_name}-svc"

        # Define the node selector if node_tag is not "none"
        node_selector = {"nodeId": node_tag} if node_tag != "none" else None

        # Create a V1Deployment object
        deployment_spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": deployment_name,
                              "blockID": block_id, "instanceID": instance_id}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": deployment_name,
                            "blockID": block_id, "instanceID": instance_id}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="redis",
                            image="bitnami/redis",
                            ports=[client.V1ContainerPort(container_port=6379)]
                        ),
                        client.V1Container(
                            name="instance",
                            image=container_image,
                            ports=[
                                client.V1ContainerPort(container_port=18000),
                                client.V1ContainerPort(container_port=18001)
                            ],
                            env=[]
                        )
                    ],
                    node_selector=node_selector
                )
            )
        )

        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=deployment_name,
                labels={"blockID": block_id, "instanceID": instance_id}
            ),
            spec=deployment_spec
        )

        deployment = add_instance_env_variables(
            deployment, block_id, instance_id, gpus)

        # Create the deployment
        apps_v1 = client.AppsV1Api()
        apps_v1.create_namespaced_deployment(
            namespace=namespace, body=deployment)

        # Create a service
        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(name=service_name),
            spec=client.V1ServiceSpec(
                selector={"app": deployment_name},
                ports=[
                    client.V1ServicePort(
                        port=6379, target_port=6379, name="redis"),
                    client.V1ServicePort(
                        port=8000, target_port=8000, name="metrics"),
                    client.V1ServicePort(
                        port=8001, target_port=8001, name="control")
                ]
            )
        )

        # Create the service
        core_v1 = client.CoreV1Api()
        core_v1.create_namespaced_service(namespace=namespace, body=service)

        logger.info(
            f"Deployment and Service for {deployment_name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create k8s deployment and service: {e}")
        raise e


def get_all_matching_instances(block_id, namespace="blocks"):
    try:

        config.load_kube_config()
        label_selector = f"blockID={block_id}"

        apps_v1 = client.AppsV1Api()
        deployments = apps_v1.list_namespaced_deployment(
            namespace=namespace, label_selector=label_selector)

        instance_ids = []
        for deployment in deployments.items:
            instance_id = deployment.metadata.labels.get("instanceID")
            if instance_id:
                instance_ids.append(instance_id)

        return instance_ids

    except Exception as e:
        raise e


def remove_executor(block_id, namespace="blocks"):
    try:
        # Load kube config
        config.load_kube_config()

        deployment_name = f"{block_id}-executor"
        service_name = f"{deployment_name}-svc"

        # Delete the deployment
        apps_v1 = client.AppsV1Api()
        delete_options = client.V1DeleteOptions()
        apps_v1.delete_namespaced_deployment(
            name=deployment_name + "-executor",
            namespace=namespace,
            body=delete_options
        )

        # Delete the service
        core_v1 = client.CoreV1Api()
        core_v1.delete_namespaced_service(
            name=service_name,
            namespace=namespace,
            body=delete_options
        )

        label_selector = f"blockID={block_id}"
        deployments = apps_v1.list_namespaced_deployment(
            namespace=namespace, label_selector=label_selector)

        delete_options = client.V1DeleteOptions()

        # Iterate over the deployments and delete each deployment and its corresponding service
        for deployment in deployments.items:
            deployment_name = deployment.metadata.name
            service_name = f"{deployment_name}-svc"

            # Delete the deployment
            apps_v1.delete_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=delete_options
            )

            # Delete the service
            core_v1.delete_namespaced_service(
                name=service_name,
                namespace=namespace,
                body=delete_options
            )

        logger.info(
            f"Deployment and Service for {deployment_name} removed successfully.")
    except Exception as e:
        logger.error(f"Failed to remove k8s deployment and service: {e}")
        raise e


def remove_single_instance(block_id, instance_id, namespace="blocks"):
    try:
        # Load kube config
        config.load_kube_config()

        deployment_name = f"{block_id}-{instance_id}"
        service_name = f"{deployment_name}-svc"

        # Delete the deployment
        apps_v1 = client.AppsV1Api()
        delete_options = client.V1DeleteOptions()
        apps_v1.delete_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=delete_options
        )

        # Delete the service
        core_v1 = client.CoreV1Api()
        core_v1.delete_namespaced_service(
            name=service_name,
            namespace=namespace,
            body=delete_options
        )

        logger.info(
            f"Deployment and Service for {deployment_name} removed successfully.")
    except Exception as e:
        logger.error(f"Failed to remove k8s deployment and service: {e}")
        raise e


def create_init_block(block_id, image_name):
    # Load the Kubernetes configuration from default location
    config.load_kube_config()

    # Create a Kubernetes API client
    apps_v1 = client.AppsV1Api()

    # Define the deployment metadata
    deployment_name = f"{block_id}-init"
    labels = {"app": deployment_name}

    cluster_id = os.getenv("CLUSTER_ID")

    controller_url = f"http://{cluster_id}-controller-svc.controllers.svc.cluster.local:4000"

    # Define the container specification
    container = client.V1Container(
        name="init-container",
        image=image_name,
        env=[
            client.V1EnvVar(name="BLOCK_SERVICE_URL",
                            value=os.getenv("BLOCKS_SERVICE_URL")),
            client.V1EnvVar(name="CLUSTER_SERVICE_URL",
                            value=os.getenv("CLUSTER_SERVICE_URL")),
            client.V1EnvVar(name="CLUSTER_ID", value=os.getenv("CLUSTER_ID")),
            client.V1EnvVar(name="OPERATING_MODE", value="creation"),
            client.V1EnvVar(name="BLOCK_ID", value=block_id),
            client.V1EnvVar(name="CONTROLLER_URL", value=controller_url),
        ]
    )

    # Define the Pod template specification
    pod_template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels=labels),
        spec=client.V1PodSpec(containers=[container])
    )

    # Define the deployment specification
    deployment_spec = client.V1DeploymentSpec(
        replicas=1,
        template=pod_template,
        selector={'matchLabels': labels}
    )

    # Define the deployment metadata
    deployment_metadata = client.V1ObjectMeta(
        name=deployment_name,
        labels=labels
    )

    # Create the deployment body
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=deployment_metadata,
        spec=deployment_spec
    )

    # Create the deployment in the default namespace
    try:
        apps_v1.create_namespaced_deployment(
            namespace="default",
            body=deployment
        )
        logger.info(f"Deployment {deployment_name} created successfully.")
    except client.exceptions.ApiException as e:
        logger.error(f"Exception when creating deployment: {e}")


def create_init_block_remove_mode(block_id, image_name):
    # Load the Kubernetes configuration from default location
    config.load_kube_config()

    # Create a Kubernetes API client
    apps_v1 = client.AppsV1Api()

    # Define the deployment metadata
    deployment_name = f"{block_id}-init"
    labels = {"app": deployment_name}

    cluster_id = os.getenv("CLUSTER_ID")

    controller_url = f"{cluster_id}-controller-svc.controllers.svc.cluster.local:4000"

    # Define the container specification
    container = client.V1Container(
        name="init-container",
        image=image_name,
        env=[
            client.V1EnvVar(name="BLOCK_SERVICE_URL",
                            value=os.getenv("BLOCKS_SERVICE_URL")),
            client.V1EnvVar(name="CLUSTER_SERVICE_URL",
                            value=os.getenv("CLUSTER_SERVICE_URL")),
            client.V1EnvVar(name="CLUSTER_ID", value=os.getenv("CLUSTER_ID")),
            client.V1EnvVar(name="OPERATING_MODE", value="remove"),
            client.V1EnvVar(name="BLOCK_ID", value=block_id),
            client.V1EnvVar(name="CONTROLLER_URL", value=controller_url),
        ]
    )

    # Define the Pod template specification
    pod_template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels=labels),
        spec=client.V1PodSpec(containers=[container])
    )

    # Define the deployment specification
    deployment_spec = client.V1DeploymentSpec(
        replicas=1,
        template=pod_template,
        selector={'matchLabels': labels}
    )

    # Define the deployment metadata
    deployment_metadata = client.V1ObjectMeta(
        name=deployment_name,
        labels=labels
    )

    # Create the deployment body
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=deployment_metadata,
        spec=deployment_spec
    )

    # Create the deployment in the default namespace
    try:
        apps_v1.create_namespaced_deployment(
            namespace="default",
            body=deployment
        )
        logger.info(f"Deployment {deployment_name} created successfully.")
    except client.exceptions.ApiException as e:
        logger.error(f"Exception when creating deployment: {e}")


def delete_init_block(block_id):
    # Load the Kubernetes configuration from default location
    config.load_kube_config()

    # Create a Kubernetes API client
    apps_v1 = client.AppsV1Api()

    deployment_name = f"{block_id}-init"

    # Delete the deployment in the default namespace
    try:
        apps_v1.delete_namespaced_deployment(
            name=deployment_name,
            namespace="default",
            body=client.V1DeleteOptions(
                propagation_policy='Foreground',
                grace_period_seconds=0
            )
        )
        logger.info(f"Deployment {deployment_name} deleted successfully.")
    except client.exceptions.ApiException as e:
        logger.error(f"Exception when deleting deployment: {e}")

def remove_deployments_with_blockID(block_id, namespace="blocks"):
    # Load Kubernetes configuration
    try:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig.")
    except Exception:
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster config.")
        except Exception as e:
            logger.error(f"Could not configure Kubernetes client: {e}")
            return

    try:
        apps_v1 = client.AppsV1Api()
        label_selector = f"blockID={block_id}"
        
        deployments = apps_v1.list_namespaced_deployment(
            namespace=namespace,
            label_selector=label_selector
        )

        if not deployments.items:
            logger.info(f"No deployments found with label blockID={block_id} in namespace '{namespace}'.")
            return

        for deployment in deployments.items:
            dep_name = deployment.metadata.name
            logger.info(f"Deleting deployment: {dep_name} in namespace: {namespace}")
            try:
                apps_v1.delete_namespaced_deployment(
                    name=dep_name,
                    namespace=namespace,
                    body=client.V1DeleteOptions()
                )
                logger.info(f"Deployment {dep_name} deleted successfully.")
            except Exception as e:
                logger.error(f"Failed to delete deployment {dep_name}: {e}")

    except Exception as e:
        logger.error(f"Error occurred during deployment cleanup: {e}")