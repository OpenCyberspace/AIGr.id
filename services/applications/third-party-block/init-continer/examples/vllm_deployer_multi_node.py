import logging
from init_container import K8sUtils, execute_init_container

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLLMMultiNodeDeployer:
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
        # Deploy vLLM using the provided LeaderWorkerSet YAML configuration
        try:
            leader_worker_set_manifest = self.load_leader_worker_set_manifest()
            K8sUtils.create_deployment(
                self.k8s, self.cluster_data['namespace'], leader_worker_set_manifest)
            logger.info("vLLM LeaderWorkerSet deployment initiated.")
            return True, "Main execution successful."
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False, str(e)

    def finish(self):
        # Finalization logic if any
        logger.info("Deployment process finished.")
        return True, "Finalization successful."

    def load_leader_worker_set_manifest(self):
        # Load or generate the LeaderWorkerSet YAML manifest
        # Replace this with actual logic to load/generate the YAML
        leader_worker_set_manifest = {
            "apiVersion": "leaderworkerset.x-k8s.io/v1",
            "kind": "LeaderWorkerSet",
            "metadata": {
                "name": "vllm"
            },
            "spec": {
                "replicas": 2,
                "leaderWorkerTemplate": {
                    "size": 2,
                    "restartPolicy": "RecreateGroupOnPodRestart",
                    "leaderTemplate": {
                        "metadata": {
                            "labels": {
                                "role": "leader"
                            }
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": "vllm-leader",
                                    "image": "kube-ai-registry.cn-shanghai.cr.aliyuncs.com/kube-ai/vllm:0.4.1",
                                    "env": [
                                        {
                                            "name": "RAY_CLUSTER_SIZE",
                                            "valueFrom": {
                                                "fieldRef": {
                                                    "fieldPath": "metadata.annotations['leaderworkerset.sigs.k8s.io/size']"
                                                }
                                            }
                                        }
                                    ],
                                    "command": [
                                        "sh", "-c",
                                        "/vllm-workspace/ray_init.sh leader --ray_cluster_size=$RAY_CLUSTER_SIZE; "
                                        "python3 -m vllm.entrypoints.openai.api_server --port 8080 --model facebook/opt-125m --swap-space 2 --tensor-parallel-size 2"
                                    ],
                                    "resources": {
                                        "limits": {
                                            "nvidia.com/gpu": "1"
                                        },
                                        "requests": {
                                            "cpu": "4",
                                            "memory": "8Gi",
                                            "nvidia.com/gpu": "1"
                                        }
                                    },
                                    "ports": [
                                        {
                                            "containerPort": 8080
                                        }
                                    ],
                                    "readinessProbe": {
                                        "tcpSocket": {
                                            "port": 8080
                                        },
                                        "initialDelaySeconds": 15,
                                        "periodSeconds": 10
                                    }
                                }
                            ]
                        }
                    },
                    "workerTemplate": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "vllm-worker",
                                    "image": "kube-ai-registry.cn-shanghai.cr.aliyuncs.com/kube-ai/vllm:0.4.1",
                                    "command": [
                                        "sh", "-c",
                                        "/vllm-workspace/ray_init.sh worker --ray_address=$(LEADER_NAME).$(LWS_NAME).$(NAMESPACE).svc.cluster.local"
                                    ],
                                    "resources": {
                                        "limits": {
                                            "nvidia.com/gpu": "1"
                                        },
                                        "requests": {
                                            "cpu": "4",
                                            "memory": "8Gi",
                                            "nvidia.com/gpu": "1"
                                        }
                                    },
                                    "env": [
                                        {
                                            "name": "LEADER_NAME",
                                            "valueFrom": {
                                                "fieldRef": {
                                                    "fieldPath": "metadata.annotations['leaderworkerset.sigs.k8s.io/leader-name']"
                                                }
                                            }
                                        },
                                        {
                                            "name": "NAMESPACE",
                                            "valueFrom": {
                                                "fieldRef": {
                                                    "fieldPath": "metadata.namespace"
                                                }
                                            }
                                        },
                                        {
                                            "name": "LWS_NAME",
                                            "valueFrom": {
                                                "fieldRef": {
                                                    "fieldPath": "metadata.labels['leaderworkerset.sigs.k8s.io/name']"
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            }
        }
        return leader_worker_set_manifest


if __name__ == "__main__":
    execute_init_container(VLLMMultiNodeDeployer)
