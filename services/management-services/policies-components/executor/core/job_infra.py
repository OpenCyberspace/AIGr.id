import threading
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import json
import os
import requests


class PolicyJobInfra:
    def __init__(self):
        self.mode = os.getenv("MODE", "k8s").lower()

        if self.mode == "k8s":
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()

            self.core_api = client.CoreV1Api()
            self.batch_api = client.BatchV1Api()
            self.namespace = "policies"
            self._ensure_namespace()

    def _ensure_namespace(self):
        if self.mode != "k8s":
            return
        try:
            self.core_api.read_namespace(name=self.namespace)
        except ApiException as e:
            if e.status == 404:
                namespace_body = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=self.namespace))
                self.core_api.create_namespace(namespace_body)
            else:
                raise

    def create_job(self, name, policy_rule_uri, job_id, redis_host, redis_queue_name, policy_rule_parameters=None, node_selector=None, inputs={}):
        if self.mode == "k8s":
            self._create_k8s_job(name, policy_rule_uri, job_id, redis_host,
                                 redis_queue_name, policy_rule_parameters, node_selector, inputs)
        elif self.mode == "openfaas":
            self._invoke_openfaas_function(
                name, policy_rule_uri, job_id, redis_host, redis_queue_name, policy_rule_parameters, inputs)
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")

    def _create_k8s_job(self, name, policy_rule_uri, job_id, redis_host, redis_queue_name, policy_rule_parameters, node_selector, inputs):
        try:
            container_env = [
                client.V1EnvVar(name="POLICY_RULE_URI", value=policy_rule_uri),
                client.V1EnvVar(name="POLICY_INPUTS",
                                value=json.dumps(inputs)),
                client.V1EnvVar(name="JOB_OUTPUT_REDIS_HOST",
                                value=redis_host),
                client.V1EnvVar(name="JOB_OUTPUT_REDIS_QUEUE_NAME",
                                value=redis_queue_name),
                client.V1EnvVar(name="JOB_ID", value=job_id),
                client.V1EnvVar(name="POLICY_DB_URL",
                                value=os.getenv("POLICY_DB_URL"))
            ]

            if policy_rule_parameters:
                container_env.append(
                    client.V1EnvVar(name="POLICY_RULE_PARAMETERS",
                                    value=json.dumps(policy_rule_parameters))
                )

            container = client.V1Container(
                name=name,
                image=os.getenv("DEFAULT_POLICY_JOB_CONTAINER_IMAGE_NAME"),
                env=container_env,
                ports=[client.V1ContainerPort(container_port=5000)]
            )

            pod_spec = client.V1PodSpec(
                restart_policy="Never",
                containers=[container]
            )

            if node_selector:
                pod_spec.node_selector = node_selector

            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"job-name": name}),
                spec=pod_spec
            )

            job_spec = client.V1JobSpec(
                template=template,
                backoff_limit=4,
                ttl_seconds_after_finished=3600
            )

            job = client.V1Job(
                api_version="batch/v1",
                kind="Job",
                metadata=client.V1ObjectMeta(
                    name=name, namespace=self.namespace),
                spec=job_spec
            )

            self.batch_api.create_namespaced_job(
                namespace=self.namespace, body=job)
            print(f"Job '{name}' created successfully.")

            monitor_thread = threading.Thread(
                target=self._monitor_job_completion, args=(name,))
            monitor_thread.daemon = True
            monitor_thread.start()
        except ApiException as e:
            raise Exception(f"Error creating job: {e}")

    def _invoke_openfaas_function(self, name, policy_rule_uri, job_id, redis_host, redis_queue_name, policy_rule_parameters, inputs):
        openfaas_gateway = os.getenv(
            "OPENFAAS_GATEWAY", "http://gateway.openfaas:8080")
        function_url = f"{openfaas_gateway}/function/{name}"

        payload = {
            "policy_rule_uri": policy_rule_uri,
            "job_id": job_id,
            "redis_host": redis_host,
            "redis_queue_name": redis_queue_name,
            "inputs": inputs
        }

        if policy_rule_parameters:
            payload["policy_rule_parameters"] = policy_rule_parameters

        response = requests.post(function_url, json=payload)
        if response.status_code == 200:
            print(f"Function '{name}' invoked successfully.")
        else:
            raise Exception(
                f"Error invoking OpenFaaS function '{name}': {response.status_code} {response.text}")

    def _monitor_job_completion(self, name):
        if self.mode != "k8s":
            return
        print(f"Monitoring job '{name}' for completion...")
        while True:
            try:
                job_status = self.batch_api.read_namespaced_job_status(
                    name=name, namespace=self.namespace).status
                if job_status.succeeded:
                    print(f"Job '{name}' has completed successfully.")
                    self.remove_job(name)
                    break
                elif job_status.failed:
                    print(f"Job '{name}' has failed.")
                    self.remove_job(name)
                    break
            except ApiException as e:
                if e.status == 404:
                    print(f"Job '{name}' no longer exists.")
                    break

            time.sleep(10)

    def remove_job(self, name):
        if self.mode != "k8s":
            return
        try:
            self.batch_api.delete_namespaced_job(
                name=name,
                namespace=self.namespace,
                body=client.V1DeleteOptions(propagation_policy="Background")
            )
            print(f"Job '{name}' deleted successfully.")
        except ApiException as e:
            if e.status != 404:
                raise Exception(f"Error removing job: {e}")
