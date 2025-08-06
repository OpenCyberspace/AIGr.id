import os
import time
import psutil
import logging

try:
    import pynvml
    pynvml.nvmlInit()
except Exception as e:
    pynvml = None
    logging.warning(f"pynvml not available: {e}")

logger = logging.getLogger(__name__)


class BlockHardwareMetrics:
    def __init__(self):
        self.nvml_available = pynvml is not None
        self.cpu_usage_last = None
        self.cpu_time_last = None

    def get_metrics(self) -> dict:
        try:
            cpu = self.get_cpu_metrics()
            memory = self.get_container_memory_usage()
            gpus = self.get_gpu_metrics() if self.nvml_available else []

            return {
                "cpu": cpu,
                "memory": memory,
                "gpus": gpus
            }
        except Exception as e:
            logger.warning(f"Failed to collect hardware metrics: {e}")
            return {}

    def get_cpu_metrics(self) -> dict:
        metrics = {}
        try:
            # Load averages (system-wide)
            load1, load5, load15 = os.getloadavg()
            metrics.update({
                "load1m": round(load1, 2),
                "load5m": round(load5, 2),
                "load15m": round(load15, 2)
            })
        except Exception as e:
            logger.warning(f"Failed to get load average: {e}")

        try:
            # Container-level CPU usage (approx %)
            if os.path.exists("/sys/fs/cgroup/cpuacct/cpuacct.usage"):  # cgroup v1
                with open("/sys/fs/cgroup/cpuacct/cpuacct.usage") as f:
                    usage_ns = int(f.read())
            elif os.path.exists("/sys/fs/cgroup/cpu.stat"):  # cgroup v2
                with open("/sys/fs/cgroup/cpu.stat") as f:
                    usage_ns = int([line for line in f if line.startswith("usage_usec")][0].split()[1]) * 1000
            else:
                return metrics

            now = time.time()
            usage_percent = None

            if self.cpu_usage_last is not None:
                elapsed_ns = usage_ns - self.cpu_usage_last
                elapsed_time = now - self.cpu_time_last
                usage_percent = round((elapsed_ns / (elapsed_time * 1e9)) * 100, 2)

            self.cpu_usage_last = usage_ns
            self.cpu_time_last = now

            if usage_percent is not None:
                metrics["percent"] = usage_percent

        except Exception as e:
            logger.warning(f"Failed to get container CPU usage: {e}")

        return metrics

    def get_container_memory_usage(self) -> dict:
        try:
            # Check cgroup v1
            if os.path.exists("/sys/fs/cgroup/memory/memory.usage_in_bytes"):
                with open("/sys/fs/cgroup/memory/memory.usage_in_bytes") as f:
                    used = int(f.read())
                with open("/sys/fs/cgroup/memory/memory.limit_in_bytes") as f:
                    limit = int(f.read())
            # Check cgroup v2
            elif os.path.exists("/sys/fs/cgroup/memory.current"):
                with open("/sys/fs/cgroup/memory.current") as f:
                    used = int(f.read())
                with open("/sys/fs/cgroup/memory.max") as f:
                    limit_str = f.read().strip()
                    limit = int(limit_str) if limit_str.isdigit() else psutil.virtual_memory().total
            else:
                mem = psutil.virtual_memory()
                return {
                    "usedMem": round(mem.used / (1024 * 1024), 2),
                    "freeMem": round(mem.available / (1024 * 1024), 2),
                    "averageUtil": mem.percent
                }

            used_mb = round(used / (1024 * 1024), 2)
            total_mb = round(limit / (1024 * 1024), 2)
            percent = round((used / limit) * 100, 2) if limit > 0 else None

            return {
                "usedMem": used_mb,
                "totalMem": total_mb,
                "averageUtil": percent
            }

        except Exception as e:
            logger.warning(f"Failed to get container memory usage: {e}")
            return {}

    def get_gpu_metrics(self) -> list:
        gpus_info = []
        try:
            num_gpus = pynvml.nvmlDeviceGetCount()
            for i in range(num_gpus):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # mW to W

                gpus_info.append({
                    "id": i,
                    "utilization": util.gpu,
                    "usedMem": round(mem_info.used / (1024 * 1024), 2),
                    "freeMem": round((mem_info.total - mem_info.used) / (1024 * 1024), 2),
                    "totalMem": round(mem_info.total / (1024 * 1024), 2),
                    "powerUtilization": round(power, 2)
                })

        except Exception as e:
            logger.warning(f"Failed to get GPU metrics: {e}")

        return gpus_info
