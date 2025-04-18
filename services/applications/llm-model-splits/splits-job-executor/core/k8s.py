import json
import logging
import os
from kubernetes import client, config

from .task_db_api import GlobalTasksDB

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


TASK_DB_STATUS_UPDATE_URL=os.getenv("TASK_DB_STATUS_UPDATE_URL")
MODEL_LAYERS_REGISTRY_URL = os.getenv("MODEL_LAYERS_REGISTRY_URL")
BLOCK_DB_URL = os.getenv("BLOCK_DB_URL")


class K8sJobsManager:
    def __init__(self, namespace="model_split_jobs"):
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config.")
        except Exception:
            config.load_kube_config()
            logger.info("Loaded kubeconfig from default location.")

        self.namespace = namespace
        self.core_v1 = client.CoreV1Api()
        self.batch_v1 = client.BatchV1Api()

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

    def _create_pv_and_pvc(self, task_id, storage_size):
        volume_name = f"task-pv-{task_id}"
        claim_name = f"task-pvc-{task_id}"

        pv = client.V1PersistentVolume(
            metadata=client.V1ObjectMeta(name=volume_name),
            spec=client.V1PersistentVolumeSpec(
                capacity={"storage": storage_size},
                access_modes=["ReadWriteOnce"],
                persistent_volume_reclaim_policy="Retain",
                host_path=client.V1HostPathVolumeSource(path=f"/mnt/data/{task_id}")
            )
        )

        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=claim_name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": storage_size}
                )
            )
        )

        logger.info("Creating PV and PVC...")
        self.core_v1.create_persistent_volume(pv)
        self.core_v1.create_namespaced_persistent_volume_claim(
            namespace=self.namespace, body=pvc
        )

        return volume_name, claim_name

    def create_job(self, task_id, task_data: dict, container_image: str, storage_size="1Gi"):
        volume_name, pvc_name = self._create_pv_and_pvc(task_id, storage_size)

        env_vars = [
            client.V1EnvVar(name="TASK_ID", value=task_id),
            client.V1EnvVar(name="TASK_DATA", value=json.dumps(task_data)),
            client.V1EnvVar(name="TASK_STATUS_UPDATE_URL", value=TASK_DB_STATUS_UPDATE_URL),
            client.V1EnvVar(name="MODEL_LAYERS_REGISTRY_URL", value=MODEL_LAYERS_REGISTRY_URL),
            client.V1EnvVar(name="BLOCK_DB_URL", value=BLOCK_DB_URL)
        ]

        volume_mount = client.V1VolumeMount(
            name="task-storage", mount_path="/mnt/task"
        )

        container = client.V1Container(
            name="task-container",
            image=container_image,
            env=env_vars,
            volume_mounts=[volume_mount]
        )

        volume = client.V1Volume(
            name="task-storage",
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                claim_name=pvc_name
            )
        )

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"task": task_id}),
            spec=client.V1PodSpec(
                restart_policy="Never",
                containers=[container],
                volumes=[volume]
            )
        )

        job_spec = client.V1JobSpec(template=template, backoff_limit=2)
        job = client.V1Job(
            metadata=client.V1ObjectMeta(name=f"job-{task_id}"),
            spec=job_spec
        )

        logger.info(f"Creating job: job-{task_id}")
        self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)

        return {
            "job_name": f"job-{task_id}",
            "pvc_name": pvc_name,
            "pv_name": volume_name,
            "namespace": self.namespace
        }



def start_new_job(task_type: str, task_data: dict, container_image: str, storage_size: str = "1Gi") -> str:
   
    tasks_db = GlobalTasksDB()

    try:
        # Step 1: Create task in global DB
        task_id = tasks_db.create_task(task_type=task_type, task_data=task_data)
        logging.info(f"Created task with ID: {task_id}")

        # Step 2: Start K8s Job using that task_id
        k8s_manager = K8sJobsManager()
        result = k8s_manager.create_job(
            task_id=task_id,
            task_data=task_data,
            container_image=container_image,
            storage_size=storage_size
        )
        logging.info(f"K8s Job launched: {result}")
        return task_id

    except Exception as e:
        logging.exception("Failed to start new job")
        raise