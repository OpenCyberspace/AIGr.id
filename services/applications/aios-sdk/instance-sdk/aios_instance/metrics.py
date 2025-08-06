import os
import threading
import time
import json
import redis

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from prometheus_client.registry import REGISTRY

from collections import deque
from .block_metrics import BlockHardwareMetrics
from .node import detect_node_id


class RollingMetric:
    def __init__(self, window_seconds=900):
        self.window = window_seconds
        self.data = deque()

    def add(self, value):
        now = time.time()
        self.data.append((now, value))
        self.cleanup(now)

    def cleanup(self, now=None):
        now = now or time.time()
        while self.data and self.data[0][0] < now - self.window:
            self.data.popleft()

    def average(self, window):
        now = time.time()
        self.cleanup(now)
        values = [v for t, v in self.data if t >= now - window]
        return sum(values) / len(values) if values else 0

    def current(self):
        self.cleanup()
        return self.data[-1][1] if self.data else 0


class AIOSMetrics:
    def __init__(self, block_id=None):
        self.block_id = block_id or os.getenv('BLOCK_ID', 'test-block')
        self.instance_id = os.getenv('INSTANCE_ID', 'instance-001')

        # Initialize Prometheus metrics
        self.metrics = {}
        self.stop_event = threading.Event()
        self.redis_client = redis.StrictRedis(
            host=os.getenv("METRICS_REDIS_HOST", "localhost"),
            port=6379,
            db=0
        )

        self.block_hardware_metrics = BlockHardwareMetrics()
        self.node_id = detect_node_id()

        # Rolling metrics
        self.rolling_metrics = {}      
        self.custom_metrics = {}        

    # Prometheus Registration
    def register_counter(self, name, documentation, labelnames=None):
        if labelnames is None:
            labelnames = []
        self.metrics[name] = Counter(
            name, documentation, labelnames=labelnames, registry=REGISTRY)

    def register_gauge(self, name, documentation, labelnames=None):
        if labelnames is None:
            labelnames = []
        self.metrics[name] = Gauge(
            name, documentation, labelnames=labelnames, registry=REGISTRY)

    def register_histogram(self, name, documentation, labelnames=None, buckets=None):
        if labelnames is None:
            labelnames = []
        if buckets is None:
            buckets = [0.1, 0.2, 0.5, 1, 2, 5, 10]
        self.metrics[name] = Histogram(
            name, documentation, labelnames=labelnames, buckets=buckets, registry=REGISTRY)

    # Prometheus Usage
    def increment_counter(self, name, labelnames=None):
        metric = self.metrics.get(name)
        if metric and isinstance(metric, Counter):
            metric.inc()

    def set_gauge(self, name, value, labelnames=None):
        metric = self.metrics.get(name)
        if metric and isinstance(metric, Gauge):
            metric.set(value)

    def observe_histogram(self, name, value, labelnames=None):
        metric = self.metrics.get(name)
        if metric and isinstance(metric, Histogram):
            metric.observe(value)

    # Rolling Metrics API
    def observe_rolling(self, name, value):
        if name not in self.rolling_metrics:
            self.rolling_metrics[name] = RollingMetric()
        self.rolling_metrics[name].add(value)

    def observe_custom_rolling(self, category, name, value):
        if category not in self.custom_metrics:
            self.custom_metrics[category] = {}
        if name not in self.custom_metrics[category]:
            self.custom_metrics[category][name] = RollingMetric()
        self.custom_metrics[category][name].add(value)

    def get_extended_metrics(self):
        summary = {}
        for name, metric in self.rolling_metrics.items():
            summary[name] = {
                "current": metric.current(),
                "average_1m": metric.average(60),
                "average_5m": metric.average(300),
                "average_15m": metric.average(900)
            }

        return summary

    # Misc
    def _get_labelnames(self, custom_labelnames=None):
        labelnames = {
            'blockID': self.block_id,
            'instanceID': self.instance_id,
            "nodeID": self.node_id
        }
        if custom_labelnames:
            labelnames.update(custom_labelnames)
        return labelnames

    def start_http_server(self, m_port=8000):
        def _run_server():
            port = int(os.getenv("METRICS_PORT", m_port))
            start_http_server(port)
            self.stop_event.wait()

        self.write_to_redis()

        server_thread = threading.Thread(target=_run_server)
        server_thread.start()

    def write_to_redis(self):
        def _write_metrics():
            while not self.stop_event.is_set():
                metrics_data = {
                    "blockId": self.block_id,
                    "instanceId": self.instance_id,
                    "nodeId": self.node_id,
                    "type": "app",
                    "timestamp": time.time()
                }

                for name, metric in self.metrics.items():
                    samples = metric.collect()[0].samples
                    for sample in samples:
                        if "_created" in sample.name:
                            continue
                        metrics_data[sample.name] = sample.value

                metrics_data['hardware'] = self.block_hardware_metrics.get_metrics()

                extended_metrics = self.get_extended_metrics()
                metrics_data.update(extended_metrics)

                try:
                    json_data = json.dumps(metrics_data)
                    self.redis_client.lpush('NODE_METRICS', json_data)
                except Exception as e:
                    print(f"Error pushing metrics to Redis: {e}")

                time.sleep(30)

        write_thread = threading.Thread(target=_write_metrics)
        write_thread.start()
