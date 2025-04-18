import json
import logging
import argparse
from kubernetes import client, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_cluster_json(data: dict):
    required_fields = ["id", "regionId", "config", "nodes", "clusterMetadata"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    if not isinstance(data["nodes"], dict) or "nodeData" not in data["nodes"]:
        raise ValueError("Invalid or missing 'nodes.nodeData'")


def parse_gpu_annotation(annotation: str):
    try:
        if not annotation or annotation.strip() == "":
            return {
                "count": 0,
                "memory": 0,
                "gpus": [],
                "features": [],
                "modelNames": []
            }

        gpus = json.loads(annotation)
        count = len(gpus)
        total_memory = sum(g.get("memory", 0) for g in gpus)
        model_names = list({g.get("modelName", "Unknown") for g in gpus})
        return {
            "count": count,
            "memory": total_memory,
            "gpus": gpus,
            "features": ["fp16"],  # Placeholder
            "modelNames": model_names
        }
    except Exception as e:
        logger.warning(f"Failed to parse GPU annotation: {e}")
        return {
            "count": 0,
            "memory": 0,
            "gpus": [],
            "features": [],
            "modelNames": []
        }


def get_node_memory_in_mb(node):
    return int(node.status.capacity['memory'].strip('Ki')) // 1024


def get_node_cpu_count(node):
    return int(node.status.capacity['cpu'])


def populate_nodes():
    config.load_kube_config()  # or config.load_incluster_config()
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    populated = []
    total_gpu_count = 0
    total_gpu_mem = 0
    total_memory = 0
    total_vcpus = 0
    total_disks = 0
    total_storage = 0
    total_network_ifaces = 0
    tx_bandwidth = 0
    rx_bandwidth = 0

    for node in nodes:
        node_name = node.metadata.name
        annotations = node.metadata.annotations or {}
        gpu_info_json = annotations.get("gpu.aios/info", "")
        gpu_info = parse_gpu_annotation(gpu_info_json)

        vcpus = get_node_cpu_count(node)
        memory = get_node_memory_in_mb(node)
        swap = 0
        disks = 1
        disk_size = 512000
        network_ifaces = 1
        tx = 10000
        rx = 10000

        populated.append({
            "id": node_name,
            "gpus": gpu_info,
            "vcpus": {"count": vcpus},
            "memory": memory,
            "swap": swap,
            "storage": {
                "disks": disks,
                "size": disk_size
            },
            "network": {
                "interfaces": network_ifaces,
                "txBandwidth": tx,
                "rxBandwidth": rx
            }
        })

        total_gpu_count += gpu_info["count"]
        total_gpu_mem += gpu_info["memory"]
        total_vcpus += vcpus
        total_memory += memory
        total_disks += disks
        total_storage += disk_size
        total_network_ifaces += network_ifaces
        tx_bandwidth += tx
        rx_bandwidth += rx

    cluster_agg = {
        "gpus": {"count": total_gpu_count, "memory": total_gpu_mem},
        "vcpus": {"count": total_vcpus},
        "memory": total_memory,
        "swap": 0,
        "storage": {"disks": total_disks, "size": total_storage},
        "network": {
            "interfaces": total_network_ifaces,
            "txBandwidth": tx_bandwidth,
            "rxBandwidth": rx_bandwidth
        }
    }

    return populated, cluster_agg


def main():
    parser = argparse.ArgumentParser(description="Populate cluster JSON with node details from Kubernetes")
    parser.add_argument("cluster_json_file", help="Path to the cluster JSON file")
    parser.add_argument("--onboard", action="store_true", help="Enable cluster onboarding to the network parser")
    parser.add_argument("--api-url", type=str, help="Base URL of the network parser (e.g., http://localhost:8000)")

    args = parser.parse_args()

    if args.onboard and not args.network_parser_url:
        parser.error("--api-url is required when --onboard is set")

    with open(args.cluster_json_file) as f:
        data = json.load(f)

    validate_cluster_json(data)

    node_data, cluster_totals = populate_nodes()
    data["nodes"]["nodeData"] = node_data
    data["nodes"]["count"] = len(node_data)

    for key, value in cluster_totals.items():
        data[key] = value

    output_file = f"{data['id']}_populated.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Updated cluster info written to {output_file}")

    if args.onboard:
        import requests
        try:
            logger.info(f"Onboarding to parser at {args.network_parser_url}/api/createCluster ...")
            response = requests.post(
                f"{args.network_parser_url.rstrip('/')}/api/createCluster",
                headers={"Content-Type": "application/json"},
                json=data
            )
            if response.status_code == 200:
                logger.info("Cluster onboarded successfully.")
            else:
                logger.error(f"Failed to onboard cluster. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            logger.error(f"Error during onboarding: {e}")


if __name__ == "__main__":
    main()
