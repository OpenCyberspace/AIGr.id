import pynvml
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class GPUManager:
    def __init__(self):
        try:
            logger.info("Initializing GPU Manager...")
            pynvml.nvmlInit()
            self.gpu_count = pynvml.nvmlDeviceGetCount()
            self.gpu_handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(self.gpu_count)]
            logger.info(f"NVML initialized successfully with {self.gpu_count} GPUs detected.")
        except pynvml.NVMLError as e:
            logger.error(f"Error initializing GPU Manager: {str(e)}")
            self.gpu_count = 0
            self.gpu_handles = []

    def count(self):
        logger.info(f"Returning GPU count: {self.gpu_count}")
        return self.gpu_count

    def collect(self):
        if not self.gpu_handles:
            logger.warning("No GPU handles found; skipping metric collection.")
            return [], {}

        per_gpu_metrics = []

        logger.info("Collecting GPU metrics...")
        for i, handle in enumerate(self.gpu_handles):
            try:
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # Convert to watts

                gpu_metrics = {
                    "gpu_id": i,
                    "usedMem": memory_info.used / (1024 ** 2),  # MB
                    "freeMem": memory_info.free / (1024 ** 2),  # MB
                    "totalMem": memory_info.total / (1024 ** 2),  # MB
                    "memUtilization": (memory_info.used / memory_info.total) * 100,
                    "cudaUtilization": utilization.gpu,
                    "powerUtilization": power_usage,
                    "temperature": temperature,
                }

                logger.debug(f"Metrics for GPU {i}: {gpu_metrics}")
                per_gpu_metrics.append(gpu_metrics)

            except pynvml.NVMLError as e:
                logger.warning(f"Failed to collect metrics for GPU {i}: {str(e)}")

        aggregated_metrics = {
            "metrics.resource.node.gpu.totalUsedMem": sum(gpu["usedMem"] for gpu in per_gpu_metrics),
            "metrics.resource.node.gpu.totalFreeMem": sum(gpu["freeMem"] for gpu in per_gpu_metrics),
            "metrics.resource.node.gpu.totalMem": sum(gpu["totalMem"] for gpu in per_gpu_metrics),
            "metrics.resource.node.gpu.avgMemUtilization": sum(gpu["memUtilization"] for gpu in per_gpu_metrics) / len(per_gpu_metrics),
            "metrics.resource.node.gpu.avgCudaUtilization": sum(gpu["cudaUtilization"] for gpu in per_gpu_metrics) / len(per_gpu_metrics),
            "metrics.resource.node.gpu.avgPowerUtilization": sum(gpu["powerUtilization"] for gpu in per_gpu_metrics) / len(per_gpu_metrics),
            "metrics.resource.node.gpu.avgTemperature": sum(gpu["temperature"] for gpu in per_gpu_metrics) / len(per_gpu_metrics),
            "metrics.resource.node.gpu.count": len(per_gpu_metrics),
        }

        logger.info("GPU metrics collection completed.")
        return aggregated_metrics, per_gpu_metrics

    def __del__(self):
        try:
            pynvml.nvmlShutdown()
            logger.info("NVML shutdown completed.")
        except Exception:
            logger.debug("Failed to shutdown NVML (possibly already shutdown or not initialized).")
