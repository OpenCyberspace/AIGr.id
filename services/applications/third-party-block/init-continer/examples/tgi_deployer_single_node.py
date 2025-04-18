import logging
from init_container import K8sUtils, execute_init_container

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TGIDeployer:
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
        # Deploy resources in the specified order: Namespace, PVC, Deployment, Service
        try:
            namespace_manifest = self.load_namespace_manifest()
            pvc_manifest = self.load_pvc_manifest()
            deployment_manifest = self.load_deployment_manifest()
            service_manifest = self.load_service_manifest()

            # Create Namespace
            K8sUtils.create_namespace(self.k8s, namespace_manifest)
            logger.info("Namespace created.")

            # Create PersistentVolumeClaim
            K8sUtils.create_pvc(self.k8s, pvc_manifest)
            logger.info("PersistentVolumeClaim created.")

            # Create Deployment
            K8sUtils.create_deployment(self.k8s, deployment_manifest)
            logger.info("Deployment created.")

            # Create Service
            K8sUtils.create_service(self.k8s, service_manifest)
            logger.info("Service created.")

            return True, "Deployment of all resources successful."
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False, str(e)

    def finish(self):
        # Finalization logic if any
        logger.info("Deployment process finished.")
        return True, "Finalization successful."

    def load_namespace_manifest(self):
        # Load or generate the Namespace YAML manifest
        return {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": "llm"
            }
        }

    def load_pvc_manifest(self):
        # Load or generate the PVC YAML manifest
        return {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": "models-cache"
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {
                    "requests": {
                        "storage": "100Gi"
                    }
                },
                "storageClassName": "gp3",
                "volumeMode": "Filesystem"
            }
        }

    def load_deployment_manifest(self):
        # Load or generate the Deployment YAML manifest
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "hf-tgi-server",
                "labels": {
                    "app": "hf-tgi-server"
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "hf-tgi-server"
                    }
                },
                "template": {
                    "metadata": {
                        "creationTimestamp": None,
                        "labels": {
                            "app": "hf-tgi-server"
                        }
                    },
                    "spec": {
                        "restartPolicy": "Always",
                        "schedulerName": "default-scheduler",
                        "terminationGracePeriodSeconds": 120,
                        "containers": [{
                            "name": "server",
                            "image": "ghcr.io/huggingface/text-generation-inference:1.3.3",
                            "ports": [{
                                "name": "http",
                                "containerPort": 3000,
                                "protocol": "TCP"
                            }],
                            "resources": {
                                "limits": {
                                    "cpu": "8",
                                    "memory": "24Gi",
                                    "nvidia.com/gpu": "1"
                                },
                                "requests": {
                                    "cpu": "6"
                                }
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": "http",
                                    "scheme": "HTTP"
                                },
                                "timeoutSeconds": 5,
                                "periodSeconds": 30,
                                "successThreshold": 1,
                                "failureThreshold": 3
                            },
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": "http",
                                    "scheme": "HTTP"
                                },
                                "timeoutSeconds": 8,
                                "periodSeconds": 100,
                                "successThreshold": 1,
                                "failureThreshold": 3
                            },
                            "env": [
                                {"name": "MODEL_ID", "value": "google/flan-t5-xl"},
                                {"name": "MAX_INPUT_LENGTH", "value": "1024"},
                                {"name": "MAX_TOTAL_TOKENS", "value": "2048"},
                                {"name": "HUGGINGFACE_HUB_CACHE",
                                    "value": "/models-cache"},
                                {"name": "PORT", "value": "3000"},
                                {"name": "HOST", "value": "0.0.0.0"}
                            ],
                            "securityContext": {
                                "capabilities": {
                                    "drop": ["ALL"]
                                },
                                "runAsNonRoot": True,
                                "allowPrivilegeEscalation": False,
                                "seccompProfile": {
                                    "type": "RuntimeDefault"
                                }
                            },
                            "volumeMounts": [
                                {"name": "models-cache",
                                    "mountPath": "/models-cache"},
                                {"name": "shm", "mountPath": "/dev/shm"}
                            ],
                            "imagePullPolicy": "IfNotPresent",
                            "startupProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": "http",
                                    "scheme": "HTTP"
                                },
                                "timeoutSeconds": 1,
                                "periodSeconds": 30,
                                "successThreshold": 1,
                                "failureThreshold": 24
                            },
                            "terminationMessagePath": "/dev/termination-log",
                            "terminationMessagePolicy": "File"
                        }],
                        "volumes": [
                            {
                                "name": "models-cache",
                                "persistentVolumeClaim": {
                                    "claimName": "models-cache"
                                }
                            },
                            {
                                "name": "shm",
                                "emptyDir": {
                                    "medium": "Memory",
                                    "sizeLimit": "1Gi"
                                }
                            }
                        ],
                        "dnsPolicy": "ClusterFirst",
                        "tolerations": [{
                            "key": "nvidia.com/gpu",
                            "operator": "Exists",
                            "effect": "NoSchedule"
                        }]
                    }
                },
                "strategy": {
                    "type": "Recreate"
                },
                "revisionHistoryLimit": 10,
                "progressDeadlineSeconds": 600
            }
        }

    def load_service_manifest(self):
        # Load or generate the Service YAML manifest
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "hf-tgi-server",
                "labels": {
                    "app": "hf-tgi-server"
                }
            },
            "spec": {
                "clusterIP": "None",
                "ipFamilies": ["IPv4"],
                "ports": [{
                    "name": "http",
                    "protocol": "TCP",
                    "port": 3000,
                    "targetPort": "http"
                }],
                "type": "ClusterIP",
                "ipFamilyPolicy": "SingleStack",
                "sessionAffinity": "None",
                "selector": {
                    "app": "hf-tgi-server"
                }
            }
        }


if __name__ == "__main__":
    execute_init_container(TGIDeployer)
