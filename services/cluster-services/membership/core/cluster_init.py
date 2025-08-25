import os
import json
import logging
from .cluster import ClusterClient
from typing import Dict, Any, List, Tuple

from kubernetes import client, config

logger = logging.getLogger(__name__)


class ClusterNodeInventory:

    GPU_ANNOTATION_KEY = "gpu.aios/info"

    def __init__(self, use_incluster_config: bool = True):
        
        if use_incluster_config:
            config.load_incluster_config()
        else:
            config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.cluster_client = ClusterClient()


    @staticmethod
    def _parse_gpu_annotation(annotation: str) -> Dict[str, Any]:
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
            if not isinstance(gpus, list):
                raise ValueError("GPU annotation JSON must be a list")

            count = len(gpus)
            total_memory = sum(int(g.get("memory", 0)) for g in gpus)
            model_names = sorted({str(g.get("modelName", "Unknown")) for g in gpus})
            return {
                "count": count,
                "memory": total_memory,
                "gpus": gpus,
                "features": ["fp16"],  # Placeholder, replace if you have real caps
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

    @staticmethod
    def _parse_cpu_quantity(q: str) -> int:
       
        s = str(q).strip().lower()
        if s.endswith("m"):
            try:
                millicores = int(s[:-1])
                return millicores // 1000
            except ValueError:
                pass
        try:
            return int(float(s))
        except ValueError:
            logger.warning(f"Unexpected CPU quantity format: {q}. Defaulting to 0.")
            return 0

    @staticmethod
    def _parse_mem_quantity_to_mb(q: str) -> int:
        
        s = str(q).strip()
        unit = s[-2:].lower() if len(s) >= 2 else ""
        try:
            if unit == "ki":
                return int(s[:-2]) // 1024
            if unit == "mi":
                return int(s[:-2])
            if unit == "gi":
                return int(s[:-2]) * 1024
            if unit == "ti":
                return int(s[:-2]) * 1024 * 1024
           
            if s.isdigit():
                return int(s) // 1024
            val = float(s)
            return int(val / (1024 * 1024))
        except Exception:
            logger.warning(f"Unexpected memory quantity format: {q}. Defaulting to 0.")
            return 0


    def collect(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        
        nodes = self.v1.list_node().items

        populated: List[Dict[str, Any]] = []
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
            gpu_info_json = annotations.get(self.GPU_ANNOTATION_KEY, "")
            gpu_info = self._parse_gpu_annotation(gpu_info_json)

            capacity = node.status.capacity or {}
            vcpus = self._parse_cpu_quantity(capacity.get("cpu", "0"))
            memory_mb = self._parse_mem_quantity_to_mb(capacity.get("memory", "0"))

            swap_mb = 0
            disks = 1
            disk_size_mb = 512000
            network_ifaces = 1
            tx = 10000
            rx = 10000

            populated.append({
                "id": node_name,
                "gpus": gpu_info,
                "vcpus": {"count": vcpus},
                "memory": memory_mb,
                "swap": swap_mb,
                "storage": {
                    "disks": disks,
                    "size": disk_size_mb
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
            total_memory += memory_mb
            total_disks += disks
            total_storage += disk_size_mb
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

    def sync_node(self):
        try:

            cluster_id = os.getenv("CLUSTER_ID")

            nodes, cluster_data = self.collect()
            update_data = {
                "nodes.nodeData": nodes,
                "nodes.count": len(nodes)
            }

            for k, v in cluster_data.items():
                update_data.update({k: v})

            return self.cluster_client.update_cluster(cluster_id, update_data)
            
        except Exception as e:
            raise e