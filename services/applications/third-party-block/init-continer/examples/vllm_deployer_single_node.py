import logging
from init_container import K8sUtils, execute_init_container

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLLMDeployer:
    def __init__(self, envs, block_data, cluster_data, k8s):
        self.envs = envs
        self.block_data = block_data
        self.cluster_data = cluster_data
        self.k8s = k8s

    def begin(self):
        # Initialize the Kubernetes connection
        try:
            self.k8s.connect()
            logger.info("Kubernetes connection initialized.")
            return True, "Initialization successful."
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False, str(e)

    def main(self):
        # Deploy vLLM using the provided YAML configuration
        try:
            deployment_manifest = self.load_deployment_manifest()
            K8sUtils.create_deployment(
                self.k8s, self.cluster_data['namespace'], deployment_manifest)
            logger.info("vLLM deployment initiated.")
            return True, "Main execution successful."
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False, str(e)

    def finish(self):
        # Finalization logic if any
        logger.info("Deployment process finished.")
        return True, "Finalization successful."

    def load_deployment_manifest(self):
        # Load or generate the deployment YAML manifest
        # Replace this with actual logic to load/generate the YAML
        deployment_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "labels": {"app": "vllm-app"},
                "name": "vllm",
                "namespace": self.cluster_data['namespace']
            },
            "spec": {
                "replicas": 2,
                "selector": {"matchLabels": {"app": "vllm-app"}},
                "strategy": {
                    "rollingUpdate": {"maxSurge": "25%", "maxUnavailable": "25%"},
                    "type": "RollingUpdate"
                },
                "template": {
                    "metadata": {"labels": {"app": "vllm-app"}},
                    "spec": {
                        "containers": [
                            {
                                "command": [
                                    "python3", "-m", "vllm.entrypoints.openai.api_server",
                                    "--model", "TheBloke/Mistral-7B-Instruct-v0.2-AWQ",
                                    "--quantization=awq", "--trust-remote-code"
                                ],
                                "image": "vllm/vllm-openai:latest",
                                "imagePullPolicy": "Always",
                                "livenessProbe": {
                                    "failureThreshold": 3,
                                    "httpGet": {"path": "/health", "port": 8000, "scheme": "HTTP"},
                                    "initialDelaySeconds": 240,
                                    "periodSeconds": 5,
                                    "successThreshold": 1,
                                    "timeoutSeconds": 1
                                },
                                "name": "vllm-openai",
                                "ports": [{"containerPort": 8000, "protocol": "TCP"}],
                                "readinessProbe": {
                                    "failureThreshold": 3,
                                    "httpGet": {"path": "/health", "port": 8000, "scheme": "HTTP"},
                                    "initialDelaySeconds": 240,
                                    "periodSeconds": 5,
                                    "successThreshold": 1,
                                    "timeoutSeconds": 1
                                },
                                "resources": {
                                    "limits": {"nvidia.com/gpu": "4"},
                                    "requests": {"nvidia.com/gpu": "4"}
                                },
                                "volumeMounts": [{"mountPath": "/root/.cache/huggingface", "name": "cache-volume"}]
                            }
                        ],
                        "volumes": [{"emptyDir": {}, "name": "cache-volume"}]
                    }
                }
            }
        }
        return deployment_manifest


if __name__ == "__main__":
    execute_init_container(VLLMDeployer)
