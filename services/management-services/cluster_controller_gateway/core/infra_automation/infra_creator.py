import os
import json
from .metrics_db_service import MetricsWriterManager
from .metrics_db import MetricsDBCreator
from .metrics_daemonset import MetricsCollectorManager
from .controller import ClusterControllerInfra

from kubernetes import config, client


class NamespaceManager:
    def __init__(self, kube_config_data: str):
        config.load_kube_config_from_dict(kube_config_data)
        self.core_v1 = client.CoreV1Api()

    def ensure_namespace(self, namespace: str):
        try:
            # Check if the namespace exists
            namespaces = self.core_v1.list_namespace()
            if any(ns.metadata.name == namespace for ns in namespaces.items):
                print(f"Namespace '{namespace}' already exists.")
                return
            # Create the namespace
            namespace_body = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=namespace)
            )
            self.core_v1.create_namespace(body=namespace_body)
            print(f"Namespace '{namespace}' created successfully.")
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error while managing namespace: {e}")

    def remove(self, namespace: str):
        try:
            # Check if the namespace exists
            self.core_v1.delete_namespace(namespace)

            print(f"Namespace '{namespace}' created successfully.")
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error while managing namespace: {e}")


class KubernetesInfraCreator:
    def __init__(self, kube_config_data: str, cluster_id: str, collect_interval: str, redis_host: str, block_metrics_redis_host: str, cluster_metrics_write_interval: str, cluster_data: dict):
        self.kube_config_data = kube_config_data
        self.cluster_id = cluster_id
        self.collect_interval = collect_interval
        self.redis_host = redis_host
        self.block_metrics_redis_host = block_metrics_redis_host
        self.cluster_metrics_write_interval = cluster_metrics_write_interval
        self.namespace_manager = NamespaceManager(
            kube_config_data=kube_config_data)
        self.cluster_data = cluster_data

        self.globals = self._init_globals()

    def _init_globals(self):
        try:

            global_envs = os.getenv("GLOBAL_SERVICES_MAP", "{}")
            global_envs = json.loads(global_envs)
            return global_envs

        except Exception as e:
            raise e

    def create(self):
        try:
            # Ensure required namespaces exist
            self.namespace_manager.ensure_namespace("metrics")

            # Step 1: Create MongoDB
            mongodb_creator = MetricsDBCreator(
                kube_config_data=self.kube_config_data)
            mongodb_creator.create()

            # Infer MongoDB service URL
            mongo_service_url = f"mongodb://cluster-metrics-svc.metrics.svc.cluster.local:27017/metrics"

            # Step 2: Create metrics-writer
            metrics_writer_manager = MetricsWriterManager(
                kube_config_data=self.kube_config_data,
                redis_host_block_metrics=self.block_metrics_redis_host,
                cluster_id=self.cluster_id,
                redis_host_cluster_metrics=self.redis_host,
                write_interval=self.cluster_metrics_write_interval,
                mongo_service_url=mongo_service_url,
                globals=self.globals
            )
            metrics_writer_manager.create()

            # Step 3: Create metrics-collector
            metrics_collector_manager = MetricsCollectorManager(
                kube_config_data=self.kube_config_data,
                cluster_id=self.cluster_id,
                collect_interval=self.collect_interval,
                redis_host=self.redis_host,
                globals=self.globals
            )
            metrics_collector_manager.create()

            # Step 4: Create cluster controller:
            cluster_controller_manager = ClusterControllerInfra(
                kube_config_data=self.kube_config_data,
                cluster_id=self.cluster_id,
                env_vars={},
                cluster_data=self.cluster_data
            )

            cluster_controller_manager.create()

            # obtain global map:
            global_map = cluster_controller_manager.prepare_url_map()
            return global_map

        except Exception as e:
            raise RuntimeError(
                f"Failed to create Kubernetes infrastructure: {e}")


class KubernetesInfraRemover:
    def __init__(self, kube_config_data: str, cluster_id: str, collect_interval: str, redis_host: str, block_metrics_redis_host: str, cluster_metrics_write_interval: str, cluster_data: dict = {}):
        self.kube_config_data = kube_config_data
        self.cluster_id = cluster_id
        self.collect_interval = collect_interval
        self.redis_host = redis_host
        self.block_metrics_redis_host = block_metrics_redis_host
        self.cluster_metrics_write_interval = cluster_metrics_write_interval
        self.cluster_data = cluster_data

    def remove(self):
        try:
            # Step 3: Remove metrics-collector
            try:
                metrics_collector_manager = MetricsCollectorManager(
                    kube_config_data=self.kube_config_data,
                    cluster_id=self.cluster_id,
                    collect_interval=self.collect_interval,
                    redis_host=self.redis_host
                )
                metrics_collector_manager.remove()
            except Exception as e:
                print('failed to remove metrics collector, proceeding...')

            # Step 2: Remove metrics-writer
            try:
                metrics_writer_manager = MetricsWriterManager(
                    kube_config_data=self.kube_config_data,
                    redis_host_block_metrics=self.block_metrics_redis_host,
                    cluster_id=self.cluster_id,
                    redis_host_cluster_metrics=self.redis_host,
                    write_interval=self.cluster_metrics_write_interval,
                    mongo_service_url=f"cluster-metrics-svc.metrics.svc.cluster.local:27017"
                )
                metrics_writer_manager.remove()
            except Exception as e:
                print('failed to remove metrics-writer, proceeding...')

            # Step 3: Remove cluster controller:
            try:
                cluster_controller_infra = ClusterControllerInfra(
                    kube_config_data=self.kube_config_data,
                    cluster_id=self.cluster_id,
                    env_vars={},
                    cluster_data=self.cluster_data
                )

                cluster_controller_infra.remove()
            except Exception as e:
                print('failed to remove metrics-writer, proceeding...')

            # Step 1: Remove MongoDB
            try:
                mongodb_creator = MetricsDBCreator(
                    kube_config_data=self.kube_config_data)
                mongodb_creator.remove()
            except Exception as e:
                print('failed to remove metrics-db, proceeding...')

            try:
                # remove namespace:
                namespace_manager = NamespaceManager(
                    kube_config_data=self.kube_config_data)
                namespace_manager.remove("metrics")
            except Exception as e:
                print('failed to remove metrics namespace, proceeding...')

        except Exception as e:
            raise RuntimeError(
                f"Failed to remove Kubernetes infrastructure: {e}")


def create_cluster_infra(kube_config_data: str, cluster_id: str, cluster_data: dict):
    try:
        # Get environment variables
        collect_interval = os.environ.get("COLLECT_INTERVAL", "20")
        redis_host = os.environ.get("METRICS_REDIS_HOST", "localhost")
        block_metrics_redis_host = os.environ.get(
            "BLOCK_METRICS_GLOBAL_DB_REDIS_HOST", "localhost")
        cluster_metrics_write_interval = os.environ.get(
            "CLUSTER_METRICS_WRITE_INTERVAL", "30")

        if not (collect_interval and redis_host and block_metrics_redis_host and cluster_metrics_write_interval):
            raise ValueError(
                "One or more required environment variables are missing.")

        # Create infrastructure
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
        print("Cluster infrastructure created successfully.")
        return global_url_map
    except Exception as e:
        raise RuntimeError(f"Failed to create cluster infrastructure: {e}")


def remove_cluster_infra(kube_config_data: str, cluster_id: str, cluster_data: dict):
    try:
        # Get environment variables
        collect_interval = os.environ.get("COLLECT_INTERVAL", "20")
        redis_host = os.environ.get("METRICS_REDIS_HOST", "localhost")
        block_metrics_redis_host = os.environ.get(
            "BLOCK_METRICS_GLOBAL_DB_REDIS_HOST", "localhost")
        cluster_metrics_write_interval = os.environ.get(
            "CLUSTER_METRICS_WRITE_INTERVAL", "30")

        if not (collect_interval and redis_host and block_metrics_redis_host and cluster_metrics_write_interval):
            raise ValueError(
                "One or more required environment variables are missing.")

        # Remove infrastructure
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

        print("Cluster infrastructure removed successfully.")
    except Exception as e:
        raise RuntimeError(f"Failed to remove cluster infrastructure: {e}")
