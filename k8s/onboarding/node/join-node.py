import os
import json
import logging
import psutil
import requests
import subprocess
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)


def get_gpu_info():
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total',
             '--format=csv,noheader,nounits'],
            stdout=subprocess.PIPE, text=True
        )

        gpus = [line.split(', ') for line in result.stdout.strip().split('\n')]
        gpu_list = []
        model_names = set()
        features = set()

        for gpu in gpus:
            if len(gpu) < 2:
                continue
            model_name = gpu[0]
            memory = int(gpu[1])
            model_names.add(model_name)

            gpu_list.append({
                "modelName": model_name,
                "memory": memory,
            })

        return {
            "count": len(gpus),
            "memory": sum(g["memory"] for g in gpu_list),
            "gpus": gpu_list,
            "features": list(features),
            "modelNames": list(model_names)
        }
    except Exception as e:
        logging.warning(f"Failed to fetch GPU info: {e}")
        return {"count": 0, "memory": 0, "gpus": [], "features": [], "modelNames": []}


def get_vcpu_info():
    try:
        return {"count": psutil.cpu_count(logical=True)}
    except Exception as e:
        logging.warning(f"Failed to fetch vCPU info: {e}")
        return {"count": 0}


def get_memory_info():
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "memory": mem.total // (1024 * 1024),
            "swap": swap.total // (1024 * 1024)
        }
    except Exception as e:
        logging.warning(f"Failed to fetch memory info: {e}")
        return {"memory": 0, "swap": 0}


def get_storage_info():
    try:
        total_storage = 0
        disk_count = 0
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total_storage += usage.total // (1024 * 1024)
                disk_count += 1
            except PermissionError:
                logging.warning(f"Skipping {partition.mountpoint} due to permission error")
        return {"disks": disk_count, "size": total_storage}
    except Exception as e:
        logging.warning(f"Failed to fetch storage info: {e}")
        return {"disks": 0, "size": 0}


def get_network_info():
    try:
        net_io = psutil.net_if_stats()
        interfaces = len(net_io)
        return {
            "interfaces": interfaces,
            "txBandwidth": 0,
            "rxBandwidth": 0
        }
    except Exception as e:
        logging.warning(f"Failed to fetch network info: {e}")
        return {"interfaces": 0, "txBandwidth": 0, "rxBandwidth": 0}


def get_node_info(node_id, cluster_id):
    mem_info = get_memory_info()
    return {
        "id": node_id,
        "clusterId": cluster_id,
        "gpus": get_gpu_info(),
        "vcpus": get_vcpu_info(),
        "memory": mem_info["memory"],
        "swap": mem_info["swap"],
        "storage": get_storage_info(),
        "network": get_network_info()
    }


def add_node_to_cluster(api_url, node_id):
    node_data = get_node_info(node_id)
    payload = {
        "header": {
            "templateUri": "Parser/V1",
            "parameters": {}
        },
        "body": {
            "spec": {
                "values": node_data
            }
        }
    }

    logging.info(f"Prepared node payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            f"{api_url}/api/addNode", json=payload)
        response.raise_for_status()
        logging.info(f"Node successfully added: {response.json()}")
        return True
    except Exception as e:
        logging.error(f"Failed to add node to cluster: {e}")
        return False


def run_kubeadm_join(join_cmd):
    try:
        logging.info("Running kubeadm join command...")
        result = subprocess.run(join_cmd, shell=True, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logging.info(f"kubeadm join output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"kubeadm join failed:\n{e.stderr}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Join node to AIOS cluster")
    parser.add_argument("--node-id", required=True,
                        help="Unique identifier for this node")
    parser.add_argument("--cluster-id", required=True,
                        help="ID of the target cluster")
    parser.add_argument("--api-url", required=True,
                        help="Cluster controller API base URL")
    parser.add_argument("--kubeadm-join-cmd", required=True,
                        help="Full kubeadm join command")

    args = parser.parse_args()

    if add_node_to_cluster(args.api_url, args.node_id):
        run_kubeadm_join(args.kubeadm_join_cmd)
