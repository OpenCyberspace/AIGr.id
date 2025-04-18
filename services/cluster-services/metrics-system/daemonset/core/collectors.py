import psutil
import time
import json
import os
import redis
import threading
from flask import Flask, jsonify

from .node import detect_node_id
from .gpu import GPUManager

import logging


def bytes_to_mb(bytes_value):
    return bytes_value / (1024 * 1024)


class MemoryMetrics:
    @staticmethod
    def get_free_memory():
        return bytes_to_mb(psutil.virtual_memory().available)

    @staticmethod
    def get_used_memory():
        return bytes_to_mb(psutil.virtual_memory().used)

    @staticmethod
    def get_memory_utilization():
        return psutil.virtual_memory().percent

    @staticmethod
    def get_used_swap():
        return bytes_to_mb(psutil.swap_memory().used)

    @staticmethod
    def get_free_swap():
        return bytes_to_mb(psutil.swap_memory().free)

    @staticmethod
    def get_page_faults_per_sec():
        swap_memory = psutil.swap_memory()
        return swap_memory.sin + swap_memory.sout

    @staticmethod
    def collect():
        return {
            'metrics.resource.node.memory.freeMem': MemoryMetrics.get_free_memory(),
            'metrics.resource.node.memory.usedMem': MemoryMetrics.get_used_memory(),
            'metrics.resource.node.memory.averageUtil': MemoryMetrics.get_memory_utilization(),
            'metrics.resource.node.memory.usedSwap': MemoryMetrics.get_used_swap(),
            'metrics.resource.node.memory.freeSwap': MemoryMetrics.get_free_swap(),
            'metrics.resource.node.memory.pageFaultsPerSec': MemoryMetrics.get_page_faults_per_sec()
        }


class VCPUMetrics:
    @staticmethod
    def get_load_avg():
        return os.getloadavg()

    @staticmethod
    def get_running_threads():
        return sum([len(p.threads()) for p in psutil.process_iter()])

    @staticmethod
    def get_total_threads():
        return sum([p.num_threads() for p in psutil.process_iter()])

    @staticmethod
    def get_running_processes():
        return len(psutil.pids())

    @staticmethod
    def get_total_processes():
        return len(psutil.pids())

    @staticmethod
    def collect():
        load_avg = VCPUMetrics.get_load_avg()
        return {
            'metrics.resource.node.vcpu.load1m': load_avg[0],
            'metrics.resource.node.vcpu.load5m': load_avg[1],
            'metrics.resource.node.vcpu.load15m': load_avg[2],
            'metrics.resource.node.vcpu.runningThreads': VCPUMetrics.get_running_threads(),
            'metrics.resource.node.vcpu.runningProcesses': VCPUMetrics.get_running_processes(),
            'metrics.resource.node.vcpu.totalThreads': VCPUMetrics.get_total_threads(),
            'metrics.resource.node.vcpu.totalProcesses': VCPUMetrics.get_total_processes()
        }


class DiskMetrics:
    @staticmethod
    def get_disk_partitions():
        return psutil.disk_partitions()

    @staticmethod
    def get_disk_usage():
        return psutil.disk_usage('/')

    @staticmethod
    def get_disk_io_counters():
        return psutil.disk_io_counters()

    @staticmethod
    def get_free_disk_memory():
        return bytes_to_mb(DiskMetrics.get_disk_usage().free)

    @staticmethod
    def get_used_disk_memory():
        return bytes_to_mb(DiskMetrics.get_disk_usage().used)

    @staticmethod
    def get_max_disk_memory():
        partitions = DiskMetrics.get_disk_partitions()
        return bytes_to_mb(max([psutil.disk_usage(p.mountpoint).total for p in partitions]))

    @staticmethod
    def get_min_disk_memory():
        partitions = DiskMetrics.get_disk_partitions()
        return bytes_to_mb(min([psutil.disk_usage(p.mountpoint).total for p in partitions]))

    @staticmethod
    def get_disk_io():
        disk_io_counters = DiskMetrics.get_disk_io_counters()
        return {
            'blocksPerSec': disk_io_counters.read_count + disk_io_counters.write_count,
            'readBytes': disk_io_counters.read_bytes,
            'writeBytes': disk_io_counters.write_bytes,
            'total': disk_io_counters.read_count + disk_io_counters.write_count,
            'active': disk_io_counters.busy_time,
            'response': disk_io_counters.busy_time
        }

    @staticmethod
    def collect():
        io = DiskMetrics.get_disk_io()
        return {
            'metrics.resource.node.storage.disks.memory.freeMem': DiskMetrics.get_free_disk_memory(),
            'metrics.resource.node.storage.disks.memory.usedMem': DiskMetrics.get_used_disk_memory(),
            'metrics.resource.node.storage.disks.memory.maxDisk': DiskMetrics.get_max_disk_memory(),
            'metrics.resource.node.storage.disks.memory.minDisk': DiskMetrics.get_min_disk_memory(),
            'metrics.resource.node.storage.disks.iops.blocksPerSec': io['blocksPerSec'],
            'metrics.resource.node.storage.disks.iops.readBytes': io['readBytes'],
            'metrics.resource.node.storage.disks.iops.writeBytes': io['writeBytes'],
            'metrics.resource.node.storage.disks.iops.total': io['total'],
            'metrics.resource.node.storage.disks.iops.active': io['active'],
            'metrics.resource.node.storage.disks.iops.response': io['response']
        }


class StorageMetrics:
    @staticmethod
    def get_free_storage():
        return bytes_to_mb(psutil.disk_usage('/').free)

    @staticmethod
    def get_used_storage():
        return bytes_to_mb(psutil.disk_usage('/').used)

    @staticmethod
    def collect():
        return {
            'metrics.resource.node.storage.freeMem': StorageMetrics.get_free_storage(),
            'metrics.resource.node.storage.usedMem': StorageMetrics.get_used_storage()
        }


class NetworkMetrics:
    @staticmethod
    def get_net_io_counters():
        return psutil.net_io_counters(pernic=False)

    @staticmethod
    def get_net_io_counters_pernic():
        return psutil.net_io_counters(pernic=True)

    @staticmethod
    def collect():
        net_io_counters = NetworkMetrics.get_net_io_counters()
        net_io_counters_pernic = NetworkMetrics.get_net_io_counters_pernic()
        return {
            'metrics.resource.node.network.txBytesTotal': net_io_counters.bytes_sent,
            'metrics.resource.node.network.rxBytesTotal': net_io_counters.bytes_recv,
            # Initialize with 0 or previous values
            'metrics.resource.node.network.rxBytes1m': 0,
            'metrics.resource.node.network.rxBytes5m': 0,
            'metrics.resource.node.network.rxBytes15m': 0,
            'metrics.resource.node.network.txBytes1m': 0,
            'metrics.resource.node.network.txBytes5m': 0,
            'metrics.resource.node.network.txBytes15m': 0,
            'metrics.resource.node.network.ifaces.txBytesTotal': sum([iface.bytes_sent for iface in net_io_counters_pernic.values()]),
            'metrics.resource.node.network.ifaces.rxBytesTotal': sum([iface.bytes_recv for iface in net_io_counters_pernic.values()]),
            'metrics.resource.node.network.ifaces.rxBytes1m': 0,
            'metrics.resource.node.network.ifaces.rxBytes5m': 0,
            'metrics.resource.node.network.ifaces.rxBytes15m': 0,
            'metrics.resource.node.network.ifaces.txBytes1m': 0,
            'metrics.resource.node.network.ifaces.txBytes5m': 0,
            'metrics.resource.node.network.ifaces.txBytes15m': 0
        }


def get_cluster_id():
    cluster_id = os.getenv("CLUSTER_ID")
    if not cluster_id:
        raise Exception(f"CLUSTER_ID env variable not found")


class MetricsCollector:
    def __init__(self, redis_host):
        self.redis_host = redis_host
        self.redis_client = None
        self.app = Flask(__name__)

        self.node_id = detect_node_id()
        self.gpu = GPUManager()

        self.connect_to_redis()

    def connect_to_redis(self):
        while True:
            try:
                self.redis_client = redis.Redis(host=self.redis_host, port=6379, db=0, socket_timeout=5)
                self.redis_client.ping()  # Test connection
                print("Connected to Redis successfully.")
                break
            except redis.ConnectionError as e:
                print(f"Redis connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def ensure_redis_connection(self):
        try:
            if not self.redis_client.ping():
                print("Redis connection lost. Reconnecting...")
                self.connect_to_redis()
        except redis.ConnectionError:
            print("Redis connection error. Reconnecting...")
            self.connect_to_redis()

    def collect_all_metrics(self):
        metrics = {}

        gpu_all, gpu_each = self.gpu.collect()

        metrics.update(MemoryMetrics.collect())
        metrics.update(VCPUMetrics.collect())
        metrics.update(DiskMetrics.collect())
        metrics.update(StorageMetrics.collect())
        metrics.update(NetworkMetrics.collect())
        metrics.update(gpu_all)

        metrics['type'] = "hardware"
        metrics['nodeId'] = self.node_id
        metrics['clusterId'] = os.getenv("CLUSTER_ID")
        metrics['metrics.resource.node.gpus'] = gpu_each
        return metrics

    def run_collector(self):
        def run():
            interval = int(os.getenv("COLLECT_INTERVAL", 30))

            while True:
                self.ensure_redis_connection()  # Ensure Redis is connected before pushing data
                
                metrics = self.collect_all_metrics()

                print(f'writing metrics: {metrics}')

                try:
                    self.redis_client.lpush('NODE_METRICS', json.dumps(metrics))
                except redis.ConnectionError:
                    print("Failed to write to Redis. Reconnecting...")
                    self.connect_to_redis()
                
                time.sleep(interval)

        thread = threading.Thread(target=run)
        thread.start()

    def start_server(self):
        @self.app.route('/getNodeMetrics', methods=['GET'])
        def get_node_metrics():
            metrics = self.collect_all_metrics()
            return jsonify(metrics)

        self.app.run(debug=False, threaded=True, host='0.0.0.0', port=int(os.getenv("PORT", 9999)))

