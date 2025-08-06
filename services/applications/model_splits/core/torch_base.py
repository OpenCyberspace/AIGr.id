import logging
from typing import List
from typing import Dict, List
from .k8s_objects_client import RemoteK8sExecutor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def torch_rank_processor(
    cluster_id: str,
    node_id: str,
    rank: int,
    nnodes: int,
    pod_name_prefix: str,
    model_name: str,
    image: str,
    nvidia_visible_devices: str,
    nccl_socket_ifname: str,
    master_service_url: str,
    master_port: int,
    namespace: str = "splits"
):

    try:
        pod_name = f"{pod_name_prefix}-rank-{rank}"
        role_label = "master" if rank == 0 else "worker"

        env_vars = [
            {"name": "NCCL_SOCKET_IFNAME", "value": nccl_socket_ifname},
            {"name": "NCCL_IB_DISABLE", "value": "1"},
            {"name": "NCCL_P2P_LEVEL", "value": "SYS"},
            {"name": "CUDA_VISIBLE_DEVICES", "value": nvidia_visible_devices},
            {"name": "NVIDIA_VISIBLE_DEVICES", "value": nvidia_visible_devices},
            {"name": "NVIDIA_DRIVER_CAPABILITIES", "value": "all"},
            {"name": "MODEL_NAME", "value": model_name},
            {"name": "NCCL_DEBUG", "value": "INFO"},
            {"name": "MAX_NEW_TOKENS", "value": "2048"}
        ]

        pod_spec = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": namespace,
                "labels": {
                    "app": "torchrun",
                    "role": role_label
                }
            },
            "spec": {
                "restartPolicy": "Never",
                "nodeSelector": {
                    "kubernetes.io/hostname": node_id
                },
                "containers": [
                    {
                        "name": "torch-container",
                        "image": image,
                        "imagePullPolicy": "Always",
                        "command": ["sh", "-c"],
                        "ports": [
                            {"containerPort": 8080},
                            {"containerPort": 3000}
                        ],
                        "args": [
                            f"""
                            MASTER_ADDR={master_service_url}
                            MASTER_PORT={master_port}
                            torchrun \\
                                --nproc_per_node=1 \\
                                --nnodes={nnodes} \\
                                --node_rank={rank} \\
                                --master_addr=$MASTER_ADDR \\
                                --master_port=$MASTER_PORT \\
                                main.py
                            """
                        ],
                        "env": env_vars
                    }
                ]
            }
        }

        logger.info(
            f"Creating torchrun pod '{pod_name}' for rank {rank} on cluster '{cluster_id}'")
        executor = RemoteK8sExecutor(cluster_id)
        result = executor.create_objects_from_dicts([pod_spec])
        logger.info(f"Successfully created torchrun pod: {pod_name}")
        return result

    except Exception as e:
        logger.error(f"Failed to create torchrun pod for rank {rank}: {e}")
        raise


def torch_create_service(
    cluster_id: str,
    name: str,
    namespace: str = "splits"
):

    try:
        service_name = f"{name}-rank-master"

        service_spec = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": namespace
            },
            "spec": {
                "selector": {
                    "app": "torchrun",
                    "role": "master"
                },
                "ports": [
                    {
                        "port": 3000,
                        "targetPort": 3000,
                        "name": "torch"
                    },
                    {
                        "port": 8080,
                        "targetPort": 8080,
                        "name": "rest"
                    }
                ]
            }
        }

        logger.info(
            f"Creating torchrun service '{service_name}' in cluster '{cluster_id}'")
        executor = RemoteK8sExecutor(cluster_id)
        result = executor.create_objects_from_dicts([service_spec])
        logger.info(f"Successfully created service: {service_name}")
        return result

    except Exception as e:
        logger.error(f"Failed to create service '{name}': {e}")
        raise


def deploy_torch_local_cluster_ranks(
    cluster_id: str,
    deployment_name: str,
    nnodes: int,
    common_params: Dict,
    per_rank_params: List[Dict],
    namespace: str = "splits"
):

    try:
        # Create master service
        logger.info(
            f"Creating master service '{deployment_name}-rank-master'...")
        torch_create_service(
            cluster_id=cluster_id,
            name=deployment_name,
            namespace=namespace
        )

        # Deploy pods for each rank
        for rank_conf in per_rank_params:
            rank = rank_conf["rank"]
            node_id = rank_conf["node_id"]
            nccl_socket_ifname = rank_conf["nccl_socket_ifname"]
            nvidia_visible_devices = rank_conf["nvidia_visible_devices"]

            logger.info(f"Deploying rank {rank} on node '{node_id}'")

            torch_rank_processor(
                cluster_id=cluster_id,
                node_id=node_id,
                rank=rank,
                nnodes=nnodes,
                pod_name_prefix=deployment_name,
                model_name=common_params["model_name"],
                image=common_params["image"],
                nvidia_visible_devices=nvidia_visible_devices,
                nccl_socket_ifname=nccl_socket_ifname,
                master_service_url=f"{deployment_name}-rank-master.{namespace}.svc.cluster.local",
                master_port=common_params["master_port"],
                namespace=namespace
            )

        logger.info("Successfully deployed all torchrun rank pods.")

    except Exception as e:
        logger.error(f"Failed to deploy torch local cluster ranks: {e}")
        raise
