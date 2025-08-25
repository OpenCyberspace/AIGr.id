import os
import json
import logging
import traceback
from kubernetes import config, client

from .metrics_db_service import MetricsWriterManager
from .metrics_db import MetricsDBCreator
from .metrics_daemonset import MetricsCollectorManager
from .controller import ClusterControllerInfra
from .objects import NamespaceAdminBinder, BootstrapTokenWriterInstaller
from .controllers_2 import ControllersStackManager
# Configure logging
logger = logging.getLogger(__name__)


class NamespaceManager:
    def __init__(self, kube_config_data: str):
        config.load_kube_config_from_dict(kube_config_data)
        self.core_v1 = client.CoreV1Api()

    def ensure_namespace(self, namespace: str):
        try:
            logger.info(f"Checking if namespace '{namespace}' exists...")
            namespaces = self.core_v1.list_namespace()
            if any(ns.metadata.name == namespace for ns in namespaces.items):
                logger.info(f"Namespace '{namespace}' already exists.")
                return
            logger.info(f"Creating namespace '{namespace}'...")
            namespace_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
            self.core_v1.create_namespace(body=namespace_body)
            logger.info(f"Namespace '{namespace}' created successfully.")
        except Exception as e:
            logger.error(f"Failed to ensure namespace '{namespace}': {e}")
            raise RuntimeError(f"Unexpected error while managing namespace: {e}")

    def remove(self, namespace: str):
        try:
            logger.info(f"Removing namespace '{namespace}'...")
            self.core_v1.delete_namespace(namespace)
            logger.info(f"Namespace '{namespace}' removed successfully.")
        except Exception as e:
            logger.error(f"Failed to remove namespace '{namespace}': {e}")
            raise RuntimeError(f"Unexpected error while managing namespace: {e}")


class KubernetesInfraCreator:
    def __init__(self, kube_config_data: str, cluster_id: str, collect_interval: str,
                 redis_host: str, block_metrics_redis_host: str,
                 cluster_metrics_write_interval: str, cluster_data: dict):
        self.kube_config_data = kube_config_data
        self.cluster_id = cluster_id
        self.collect_interval = collect_interval
        self.redis_host = redis_host
        self.block_metrics_redis_host = block_metrics_redis_host
        self.cluster_metrics_write_interval = cluster_metrics_write_interval
        self.namespace_manager = NamespaceManager(kube_config_data=kube_config_data)
        self.cluster_data = cluster_data
        self.globals = self._init_globals()

    def _init_globals(self):
        try:
            logger.info("Loading GLOBAL_SERVICES_MAP from environment...")
            global_envs = os.getenv("GLOBAL_SERVICES_MAP", "{}")
            return json.loads(global_envs)
        except Exception as e:
            logger.error(f"Failed to parse GLOBAL_SERVICES_MAP: {e}")
            raise

    def create(self):
        try:
            logger.info("Starting infrastructure creation...")

            self.namespace_manager.ensure_namespace("metrics")
            self.namespace_manager.ensure_namespace("controllers")

            logger.info("Ensuring ClusterRoleBindings for default SAs via NamespaceAdminBinder...")
            binder = NamespaceAdminBinder(kube_config_data=self.kube_config_data)
            binder_status = binder.ensure_all()
            logger.info("NamespaceAdminBinder status: %s", binder_status)

            # === Bootstrap Token Writer (kube-system Role + RoleBinding) ===
            logger.info("Installing bootstrap-token-writer Role and RoleBinding...")
            btw_installer = BootstrapTokenWriterInstaller(
                kube_config_data=self.kube_config_data,
                role_namespace="kube-system",
                role_name="bootstrap-token-writer",
                subject_sa_name="default",
                subject_sa_namespace="default",
            )
            btw_status = btw_installer.ensure_all()
            logger.info("BootstrapTokenWriterInstaller status: %s", btw_status)

            logger.info("Creating MongoDB for metrics...")
            mongodb_creator = MetricsDBCreator(kube_config_data=self.kube_config_data)
            mongodb_creator.create()

            mongo_service_url = "mongodb://cluster-metrics-svc.metrics.svc.cluster.local:27017/metrics"

            logger.info("Creating metrics-writer service...")
            metrics_writer_manager = MetricsWriterManager(
                kube_config_data=self.kube_config_data,
                redis_host_block_metrics=self.block_metrics_redis_host,
                cluster_id=self.cluster_id,
                redis_host_cluster_metrics=self.redis_host,
                write_interval=self.cluster_metrics_write_interval,
                mongo_service_url=mongo_service_url,
                globals=self.globals,
                cluster_data=self.cluster_data
            )
            metrics_writer_manager.create()

            logger.info("Creating metrics-collector daemonset...")
            metrics_collector_manager = MetricsCollectorManager(
                kube_config_data=self.kube_config_data,
                cluster_id=self.cluster_id,
                collect_interval=self.collect_interval,
                redis_host=self.redis_host,
                globals=self.globals,
                cluster_data=self.cluster_data
            )
            metrics_collector_manager.create()

            logger.info("Creating cluster controller deployment...")
            cluster_controller_manager = ClusterControllerInfra(
                kube_config_data=self.kube_config_data,
                cluster_id=self.cluster_id,
                env_vars={},
                cluster_data=self.cluster_data,
                globals=self.globals
            )
            cluster_controller_manager.create()

            logger.info("Preparing global service URL map...")
            global_map = cluster_controller_manager.prepare_url_map()


            logger.info("Deploying controllers stack (membership-server, grpc-proxy)...")
            controllers_mgr = ControllersStackManager(
                kube_config_data=self.kube_config_data,
                namespace="controllers",
                membership_image=os.getenv(
                    "MEMBERSHIP_SERVER_IMAGE",
                    "34.58.1.86:31280/cluster/membership:latest",
                ),
                grpc_proxy_image=os.getenv(
                    "GRPC_PROXY_IMAGE",
                    "34.58.1.86:31280/cluster/rpc:latest",
                ),
                membership_node_port=int(os.getenv("MEMBERSHIP_NODE_PORT", "30501")),
                grpc_proxy_node_port=int(os.getenv("GRPC_PROXY_NODE_PORT", "32000")),
                cluster_id=self.cluster_id,
                cluster_metrics_service_url=os.getenv(
                    "CLUSTER_METRICS_SERVICE_URL",
                    "http://metrics-writer-svc.metrics.svc.cluster.local:5000",
                ),
                policy_db_url=os.getenv("POLICY_DB_URL", "http://34.58.1.86:30102"),
                policy_execution_mode=os.getenv("POLICY_EXECUTION_MODE", "local")
            )
            controllers_status = controllers_mgr.create()
            logger.info("Controllers stack deployed: %s", controllers_status)


            logger.info("Infrastructure created successfully.")

            return global_map

        except Exception as e:
            logger.error(f"Error during infrastructure creation: {e}")
            raise RuntimeError(f"Failed to create Kubernetes infrastructure: {e}")


class KubernetesInfraRemover:
    def __init__(self, kube_config_data: str, cluster_id: str, collect_interval: str,
                 redis_host: str, block_metrics_redis_host: str,
                 cluster_metrics_write_interval: str, cluster_data: dict = {}):
        self.kube_config_data = kube_config_data
        self.cluster_id = cluster_id
        self.collect_interval = collect_interval
        self.redis_host = redis_host
        self.block_metrics_redis_host = block_metrics_redis_host
        self.cluster_metrics_write_interval = cluster_metrics_write_interval
        self.cluster_data = cluster_data

    def remove(self):
        try:
            logger.info("Starting infrastructure teardown...")

            try:
                logger.info("Removing grpc-proxy and membership-server (controllers stack)...")
                controllers_mgr = ControllersStackManager(
                    kube_config_data=self.kube_config_data,
                    namespace="controllers",
                )
                controllers_mgr.remove()
            except Exception as e:
                logger.warning(f"Failed to remove controllers stack (grpc-proxy/membership-server): {e}")

            try:
                logger.info("Removing metrics-collector...")
                metrics_collector_manager = MetricsCollectorManager(
                    kube_config_data=self.kube_config_data,
                    cluster_id=self.cluster_id,
                    collect_interval=self.collect_interval,
                    redis_host=self.redis_host
                )
                metrics_collector_manager.remove()
            except Exception as e:
                logger.warning(f"Failed to remove metrics-collector: {e}")

            try:
                logger.info("Removing metrics-writer...")
                metrics_writer_manager = MetricsWriterManager(
                    kube_config_data=self.kube_config_data,
                    redis_host_block_metrics=self.block_metrics_redis_host,
                    cluster_id=self.cluster_id,
                    redis_host_cluster_metrics=self.redis_host,
                    write_interval=self.cluster_metrics_write_interval,
                    mongo_service_url="cluster-metrics-svc.metrics.svc.cluster.local:27017",
                    cluster_data=self.cluster_data
                )
                metrics_writer_manager.remove()
            except Exception as e:
                logger.warning(f"Failed to remove metrics-writer: {e}")

            try:
                logger.info("Removing cluster controller...")
                cluster_controller_infra = ClusterControllerInfra(
                    kube_config_data=self.kube_config_data,
                    cluster_id=self.cluster_id,
                    env_vars={},
                    cluster_data=self.cluster_data,
                    globals=self
                )
                cluster_controller_infra.remove()
            except Exception as e:
                logger.warning(f"Failed to remove cluster controller: {e}")

            try:
                logger.info("Removing metrics MongoDB...")
                mongodb_creator = MetricsDBCreator(kube_config_data=self.kube_config_data)
                mongodb_creator.remove()
            except Exception as e:
                logger.warning(f"Failed to remove metrics-db: {e}")

            try:
                logger.info("Removing 'metrics' namespace...")
                namespace_manager = NamespaceManager(kube_config_data=self.kube_config_data)
                namespace_manager.remove("metrics")
            except Exception as e:
                logger.warning(f"Failed to remove metrics namespace: {e}")

            logger.info("Infrastructure teardown completed.")
        except Exception as e:
            logger.error(f"Error during infrastructure removal: {e}")
            raise RuntimeError(f"Failed to remove Kubernetes infrastructure: {e}")


def create_cluster_infra(kube_config_data: str, cluster_id: str, cluster_data: dict):
    try:
        logger.info("Initializing cluster infrastructure creation...")
        collect_interval = os.getenv("COLLECT_INTERVAL", "20")
        redis_host = os.getenv("METRICS_REDIS_HOST", "localhost")
        block_metrics_redis_host = os.getenv("BLOCK_METRICS_GLOBAL_DB_REDIS_HOST", "localhost")
        cluster_metrics_write_interval = os.getenv("CLUSTER_METRICS_WRITE_INTERVAL", "30")

        if not (collect_interval and redis_host and block_metrics_redis_host and cluster_metrics_write_interval):
            raise ValueError("One or more required environment variables are missing.")
            

        infra_creator = KubernetesInfraCreator(
            kube_config_data=kube_config_data,
            cluster_id=cluster_id,
            collect_interval=collect_interval,
            redis_host=redis_host,
            block_metrics_redis_host=block_metrics_redis_host,
            cluster_metrics_write_interval=cluster_metrics_write_interval,
            cluster_data=cluster_data
        )

        global_url_map = infra_creator.create()
        logger.info("Cluster infrastructure created successfully.")
        return global_url_map
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Cluster infrastructure creation failed: {e}")
        raise RuntimeError(f"Failed to create cluster infrastructure: {e}")


def remove_cluster_infra(kube_config_data: str, cluster_id: str, cluster_data: dict):
    try:
        logger.info("Initializing cluster infrastructure removal...")
        collect_interval = os.environ.get("COLLECT_INTERVAL", "20")
        redis_host = os.environ.get("METRICS_REDIS_HOST", "localhost")
        block_metrics_redis_host = os.environ.get("BLOCK_METRICS_GLOBAL_DB_REDIS_HOST", "localhost")
        cluster_metrics_write_interval = os.environ.get("CLUSTER_METRICS_WRITE_INTERVAL", "30")

        if not (collect_interval and redis_host and block_metrics_redis_host and cluster_metrics_write_interval):
            raise ValueError("One or more required environment variables are missing.")

        infra_remover = KubernetesInfraRemover(
            kube_config_data=kube_config_data,
            cluster_id=cluster_id,
            collect_interval=collect_interval,
            redis_host=redis_host,
            block_metrics_redis_host=block_metrics_redis_host,
            cluster_metrics_write_interval=cluster_metrics_write_interval,
            cluster_data=cluster_data
        )
    
        infra_remover.remove()

        logger.info("Cluster infrastructure removed successfully.")
    except Exception as e:
        logger.error(f"Cluster infrastructure removal failed: {e}")
        raise RuntimeError(f"Failed to remove cluster infrastructure: {e}")
