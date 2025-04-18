import pynvml
import logging


class GPUManager:
    def __init__(self):

        try:
            print(f"GPU initializing")
            pynvml.nvmlInit()  # Initialize NVML
            self.gpu_count = pynvml.nvmlDeviceGetCount()
            self.gpu_handles = [pynvml.nvmlDeviceGetHandleByIndex(
                i) for i in range(self.gpu_count)]

            print(f"NVML initialized")
        except pynvml.NVMLError as e:
            print(f"Error initializing GPU Manager: {str(e)}")
            self.gpu_count = 0
            self.gpu_handles = []

    def count(self):
        return self.gpu_count

    def collect(self):

        if not self.gpu_handles:
            return [], {}

        per_gpu_metrics = []

        for i, handle in enumerate(self.gpu_handles):
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temperature = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU)
            power_usage = pynvml.nvmlDeviceGetPowerUsage(
                handle) / 1000  # Convert to watts
            # power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(
            #    handle) / 1000  # Convert to watts

            gpu_metrics = {
                "gpu_id": i,
                "usedMem": memory_info.used / (1024 ** 2),  # Convert to MB
                "freeMem": memory_info.free / (1024 ** 2),  # Convert to MB
                "totalMem": memory_info.total / (1024 ** 2),  # Convert to MB
                "memUtilization": (memory_info.used / memory_info.total) * 100,
                "cudaUtilization": utilization.gpu,
                "powerUtilization": 0,
                "temperature": temperature,  # Celsius
            }
            per_gpu_metrics.append(gpu_metrics)

        aggregated_metrics = {
            "metrics.resource.node.gpu.totalUsedMem": sum(gpu["usedMem"] for gpu in per_gpu_metrics),
            "metrics.resource.node.gpu.totalFreeMem": sum(gpu["freeMem"] for gpu in per_gpu_metrics),
            "metrics.resource.node.gpu.totalMem": sum(gpu["totalMem"] for gpu in per_gpu_metrics),
            "metrics.resource.node.gpu.avgMemUtilization": sum(gpu["memUtilization"] for gpu in per_gpu_metrics) / len(per_gpu_metrics),
            "metrics.resource.node.gpu.avgCudaUtilization": sum(gpu["cudaUtilization"] for gpu in per_gpu_metrics) / len(per_gpu_metrics),
            "metrics.resource.node.gpu.avgPowerUtilization": sum(gpu["powerUtilization"] for gpu in per_gpu_metrics) / len(per_gpu_metrics),
            "metrics.resource.node.gpu.avgTemperature": sum(gpu["temperature"] for gpu in per_gpu_metrics) / len(per_gpu_metrics),
            "metrics.resource.node.gpu.count": len(per_gpu_metrics)
        }

        return aggregated_metrics, per_gpu_metrics

    def __del__(self):

        try:
            pynvml.nvmlShutdown()
        except:
            pass
