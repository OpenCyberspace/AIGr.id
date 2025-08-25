import logging
from typing import List, Optional, Dict

from kubernetes import client, config
from kubernetes.client import ApiException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class NamespaceAdminBinder:
    DEFAULT_NAMESPACES = ["blocks", "controllers", "metrics", "vdags", "default"]

    def __init__(
        self,
        kube_config_data: dict,
        namespaces: Optional[List[str]] = None,
        service_account_name: str = "default",
        cluster_role_name: str = "cluster-admin",
    ):
        config.load_kube_config_from_dict(kube_config_data)
        self.core_api = client.CoreV1Api()
        self.rbac_api = client.RbacAuthorizationV1Api()
        self.namespaces = namespaces or self.DEFAULT_NAMESPACES
        self.service_account_name = service_account_name
        self.cluster_role_name = cluster_role_name

    def ensure_namespace(self, namespace: str) -> str:
        try:
            self.core_api.read_namespace(namespace)
            logging.info("namespace exists: %s", namespace)
            return "exists"
        except ApiException as e:
            if e.status == 404:
                self.core_api.create_namespace(
                    client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
                )
                logging.info("namespace created: %s", namespace)
                return "created"
            logging.exception("failed to read/create namespace: %s", namespace)
            raise

    def ensure_service_account(self, namespace: str, sa_name: str) -> str:
        if sa_name == "default":
            logging.info("serviceaccount skipped (default auto-managed): %s/%s", namespace, sa_name)
            return "skipped"
        try:
            self.core_api.read_namespaced_service_account(sa_name, namespace)
            logging.info("serviceaccount exists: %s/%s", namespace, sa_name)
            return "exists"
        except ApiException as e:
            if e.status == 404:
                self.core_api.create_namespaced_service_account(
                    namespace,
                    client.V1ServiceAccount(metadata=client.V1ObjectMeta(name=sa_name)),
                )
                logging.info("serviceaccount created: %s/%s", namespace, sa_name)
                return "created"
            logging.exception("failed to read/create serviceaccount: %s/%s", namespace, sa_name)
            raise

    def _build_crb(self, namespace: str) -> client.V1ClusterRoleBinding:
        subject_dict = {
            "kind": "ServiceAccount",
            "name": self.service_account_name,
            "namespace": namespace,
            "apiGroup": "",  # core
        }
        role_ref = client.V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="ClusterRole",
            name=self.cluster_role_name,
        )
        metadata = client.V1ObjectMeta(name=f"{namespace}-ns")
        return client.V1ClusterRoleBinding(metadata=metadata, subjects=[subject_dict], role_ref=role_ref)

    def ensure_bindings(self) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for ns in self.namespaces:
            name = f"{ns}-ns"
            body = self._build_crb(ns)
            try:
                self.rbac_api.read_cluster_role_binding(name)
                self.rbac_api.replace_cluster_role_binding(name=name, body=body)
                logging.info("clusterrolebinding updated: %s (namespace=%s)", name, ns)
                results[name] = "updated"
            except ApiException as e:
                if e.status == 404:
                    self.rbac_api.create_cluster_role_binding(body=body)
                    logging.info("clusterrolebinding created: %s (namespace=%s)", name, ns)
                    results[name] = "created"
                else:
                    logging.exception("failed to ensure clusterrolebinding: %s", name)
                    results[name] = f"error: {e}"
        return results

    def ensure_all(self) -> Dict[str, Dict[str, str]]:
        ns_results: Dict[str, str] = {}
        sa_results: Dict[str, str] = {}
        for ns in self.namespaces:
            ns_results[ns] = self.ensure_namespace(ns)
            sa_results[ns] = self.ensure_service_account(ns, self.service_account_name)
        crb_results = self.ensure_bindings()
        return {"namespaces": ns_results, "service_accounts": sa_results, "cluster_role_bindings": crb_results}


class BootstrapTokenWriterInstaller:
    def __init__(
        self,
        kube_config_data: dict,
        role_namespace: str = "kube-system",
        role_name: str = "bootstrap-token-writer",
        subject_sa_name: str = "default",
        subject_sa_namespace: str = "default",
    ):
        config.load_kube_config_from_dict(kube_config_data)
        self.rbac = client.RbacAuthorizationV1Api()
        self.role_namespace = role_namespace
        self.role_name = role_name
        self.subject_sa_name = subject_sa_name
        self.subject_sa_namespace = subject_sa_namespace

    def _build_role(self) -> client.V1Role:
        metadata = client.V1ObjectMeta(name=self.role_name, namespace=self.role_namespace)
        rules = [client.V1PolicyRule(api_groups=[""], resources=["secrets"], verbs=["create"])]
        return client.V1Role(metadata=metadata, rules=rules)

    def _build_role_binding(self) -> client.V1RoleBinding:
        metadata = client.V1ObjectMeta(name=f"{self.role_name}-binding", namespace=self.role_namespace)
        subject_dict = {
            "kind": "ServiceAccount",
            "name": self.subject_sa_name,
            "namespace": self.subject_sa_namespace,
            "apiGroup": "",
        }
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="Role", name=self.role_name)
        return client.V1RoleBinding(metadata=metadata, subjects=[subject_dict], role_ref=role_ref)

    def ensure_role(self) -> str:
        body = self._build_role()
        try:
            existing = self.rbac.read_namespaced_role(name=self.role_name, namespace=self.role_namespace)
            body.metadata.resource_version = existing.metadata.resource_version
            self.rbac.replace_namespaced_role(name=self.role_name, namespace=self.role_namespace, body=body)
            logging.info("role updated: %s/%s", self.role_namespace, self.role_name)
            return "updated"
        except ApiException as e:
            if e.status == 404:
                self.rbac.create_namespaced_role(namespace=self.role_namespace, body=body)
                logging.info("role created: %s/%s", self.role_namespace, self.role_name)
                return "created"
            logging.exception("failed to ensure role: %s/%s", self.role_namespace, self.role_name)
            return f"error: {e}"

    def ensure_role_binding(self) -> str:
        body = self._build_role_binding()
        name = f"{self.role_name}-binding"
        try:
            existing = self.rbac.read_namespaced_role_binding(name=name, namespace=self.role_namespace)
            body.metadata.resource_version = existing.metadata.resource_version
            self.rbac.replace_namespaced_role_binding(name=name, namespace=self.role_namespace, body=body)
            logging.info("rolebinding updated: %s/%s", self.role_namespace, name)
            return "updated"
        except ApiException as e:
            if e.status == 404:
                self.rbac.create_namespaced_role_binding(namespace=self.role_namespace, body=body)
                logging.info("rolebinding created: %s/%s", self.role_namespace, name)
                return "created"
            logging.exception("failed to ensure rolebinding: %s/%s", self.role_namespace, name)
            return f"error: {e}"

    def ensure_all(self) -> Dict[str, str]:
        role_status = self.ensure_role()
        rb_status = self.ensure_role_binding()
        return {"role": role_status, "role_binding": rb_status}