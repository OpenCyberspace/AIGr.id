from pyhelm.tiller import Tiller
from pyhelm.chartbuilder import ChartBuilder
from kubernetes import watch
import logging
from kubernetes import client, config
from kubernetes.utils import create_from_yaml
from kubernetes.client.rest import ApiException
import shlex

import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class K8sConnectionError(Exception):
    """Custom exception for K8sConnection errors"""
    pass


class K8sConnection:
    def __init__(self):
        self.configuration = None
        self.api_client = None

    def connect(self):
        try:
            # Try in-cluster configuration first
            config.load_incluster_config()
            logger.info("Connected using in-cluster configuration.")
        except Exception as e:
            logger.warning(
                f"In-cluster configuration failed: {e}. Falling back to kubeconfig.")

            try:
                # Fallback to default kubeconfig file
                config.load_kube_config()
                logger.info("Connected using kubeconfig file.")
            except Exception as e:
                logger.error(f"Failed to connect using kubeconfig: {e}")
                raise K8sConnectionError(
                    f"Failed to connect to Kubernetes cluster: {e}")

        # Initialize API client
        self.configuration = client.Configuration().get_default_copy()
        self.api_client = client.ApiClient(self.configuration)

    def get_api_client(self):
        return self.api_client


class K8sUtils:
    # Deployment methods
    @staticmethod
    def list_deployments(k8s_conn, namespace):
        try:
            apps_v1 = client.AppsV1Api(k8s_conn.get_api_client())
            deployments = apps_v1.list_namespaced_deployment(namespace)
            logger.info(f"Listing deployments in namespace '{namespace}':")
            for dep in deployments.items:
                logger.info(f"{dep.metadata.name}")
            return deployments
        except ApiException as e:
            logger.error(
                f"An error occurred while listing deployments in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def update_deployment(k8s_conn, namespace, deployment_name, deployment_manifest):
        try:
            apps_v1 = client.AppsV1Api(k8s_conn.get_api_client())
            apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment_manifest
            )
            logger.info(
                f"Deployment '{deployment_name}' updated in namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while updating deployment '{deployment_name}' in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def create_deployment(k8s_conn, namespace, deployment_manifest):
        try:
            apps_v1 = client.AppsV1Api(k8s_conn.get_api_client())
            apps_v1.create_namespaced_deployment(
                body=deployment_manifest,
                namespace=namespace
            )
            logger.info(f"Deployment created in namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while creating deployment in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def delete_deployment(k8s_conn, namespace, deployment_name):
        try:
            apps_v1 = client.AppsV1Api(k8s_conn.get_api_client())
            apps_v1.delete_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            logger.info(
                f"Deployment '{deployment_name}' deleted from namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while deleting deployment '{deployment_name}' in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    # Pod methods
    @staticmethod
    def list_pods(k8s_conn, namespace):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            pods = v1.list_namespaced_pod(namespace)
            logger.info(f"Listing pods in namespace '{namespace}':")
            for pod in pods.items:
                logger.info(f"{pod.metadata.name}")
            return pods
        except ApiException as e:
            logger.error(
                f"An error occurred while listing pods in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def delete_pod(k8s_conn, namespace, pod_name):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            logger.info(
                f"Pod '{pod_name}' deleted from namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while deleting pod '{pod_name}' in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def create_pod(k8s_conn, namespace, pod_manifest):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            v1.create_namespaced_pod(namespace=namespace, body=pod_manifest)
            logger.info(f"Pod created in namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while creating pod in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def update_pod(k8s_conn, namespace, pod_name, pod_manifest):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            v1.patch_namespaced_pod(
                name=pod_name, namespace=namespace, body=pod_manifest)
            logger.info(
                f"Pod '{pod_name}' updated in namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while updating pod '{pod_name}' in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    # Service methods
    @staticmethod
    def list_services(k8s_conn, namespace):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            services = v1.list_namespaced_service(namespace)
            logger.info(f"Listing services in namespace '{namespace}':")
            for svc in services.items:
                logger.info(f"{svc.metadata.name}")
            return services
        except ApiException as e:
            logger.error(
                f"An error occurred while listing services in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def delete_service(k8s_conn, namespace, service_name):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            v1.delete_namespaced_service(
                name=service_name, namespace=namespace)
            logger.info(
                f"Service '{service_name}' deleted from namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while deleting service '{service_name}' in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def create_service(k8s_conn, namespace, service_manifest):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            v1.create_namespaced_service(
                namespace=namespace, body=service_manifest)
            logger.info(f"Service created in namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while creating service in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def update_service(k8s_conn, namespace, service_name, service_manifest):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            v1.patch_namespaced_service(
                name=service_name, namespace=namespace, body=service_manifest)
            logger.info(
                f"Service '{service_name}' updated in namespace '{namespace}'.")
        except ApiException as e:
            logger.error(
                f"An error occurred while updating service '{service_name}' in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    # Watcher method
    @staticmethod
    def watch_pod_events(k8s_conn, namespace):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            w = watch.Watch()
            for event in w.stream(v1.list_namespaced_pod, namespace=namespace):
                logger.info(
                    f"Event: {event['type']} Pod: {event['object'].metadata.name}")
        except ApiException as e:
            logger.error(
                f"An error occurred while watching pod events in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def watch_deployment_events(k8s_conn, namespace):
        try:
            apps_v1 = client.AppsV1Api(k8s_conn.get_api_client())
            w = watch.Watch()
            for event in w.stream(apps_v1.list_namespaced_deployment, namespace=namespace):
                logger.info(
                    f"Event: {event['type']} Deployment: {event['object'].metadata.name}")
        except ApiException as e:
            logger.error(
                f"An error occurred while watching deployment events in namespace '{namespace}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def watch_events(k8s_conn, namespace, resource_type):
        try:
            v1 = client.CoreV1Api(k8s_conn.get_api_client())
            w = watch.Watch()
            resource_func = getattr(v1, f"list_namespaced_{resource_type}")
            for event in w.stream(resource_func, namespace=namespace):
                logger.info(
                    f"Event: {event['type']} {resource_type.capitalize()}: {event['object'].metadata.name}")
        except ApiException as e:
            logger.error(
                f"An error occurred while watching {resource_type} events in namespace '{namespace}': {e}")
            raise
        except AttributeError:
            logger.error(f"Invalid resource type: {resource_type}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    @staticmethod
    def execute_manifest(k8s_conn, manifest_path, namespace):
        try:
            k8s_client = k8s_conn.get_api_client()
            create_from_yaml(k8s_client, manifest_path, namespace=namespace)
            logger.info(
                f"Manifest '{manifest_path}' executed in namespace '{namespace}'.")
        except Exception as e:
            logger.error(
                f"An error occurred while executing manifest '{manifest_path}': {e}")
            raise


class HelmManager:
    def __init__(self, tiller_host='localhost', tiller_port=44134):
        self.tiller_host = tiller_host
        self.tiller_port = tiller_port
        self.tiller = Tiller(host=self.tiller_host, port=self.tiller_port)

    def create_helm_deployment(self, chart_path, release_name, namespace, values=None):
        try:
            chart = ChartBuilder({"name": release_name, "source": {
                                 "type": "directory", "location": chart_path}})
            if values is None:
                values = {}

            self.tiller.install_release(chart.get_helm_chart(
            ), dry_run=False, name=release_name, namespace=namespace, values=values)
            logger.info(
                f"Helm deployment '{release_name}' created in namespace '{namespace}'.")
        except Exception as e:
            logger.error(
                f"An error occurred while creating helm deployment '{release_name}': {e}")
            raise

    def delete_helm_deployment(self, release_name, namespace):
        try:
            self.tiller.uninstall_release(release_name)
            logger.info(
                f"Helm deployment '{release_name}' deleted from namespace '{namespace}'.")
        except Exception as e:
            logger.error(
                f"An error occurred while deleting helm deployment '{release_name}': {e}")
            raise

    def update_helm_deployment(self, chart_path, release_name, namespace, values=None):
        try:
            chart = ChartBuilder({"name": release_name, "source": {
                                 "type": "directory", "location": chart_path}})
            if values is None:
                values = {}

            self.tiller.update_release(chart.get_helm_chart(
            ), dry_run=False, name=release_name, namespace=namespace, values=values)
            logger.info(
                f"Helm deployment '{release_name}' updated in namespace '{namespace}'.")
        except Exception as e:
            logger.error(
                f"An error occurred while updating helm deployment '{release_name}': {e}")
            raise


class HelmSubprocessError(Exception):
    """Custom exception for HelmSubprocess errors"""
    pass


class HelmSubprocess:
    def __init__(self, helm_command='helm'):
        self.helm_command = helm_command

    def run_helm_command(self, args):
        command = [self.helm_command] + args
        try:
            logger.info(f"Executing command: {' '.join(command)}")
            result = subprocess.run(
                command, capture_output=True, text=True, check=True)
            logger.info(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(
                f"An error occurred while running helm command: {e.stderr}")
            raise HelmSubprocessError(
                f"An error occurred while running helm command: {e.stderr}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise HelmSubprocessError(f"An unexpected error occurred: {e}")

    def run_helm_command_string(self, arg_string):
        try:
            command = [self.helm_command] + shlex.split(arg_string)
            logger.info(f"Executing command: {' '.join(command)}")
            result = subprocess.run(
                command, capture_output=True, text=True, check=True)
            logger.info(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(
                f"An error occurred while running helm command: {e.stderr}")
            raise HelmSubprocessError(
                f"An error occurred while running helm command: {e.stderr}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise HelmSubprocessError(f"An unexpected error occurred: {e}")
