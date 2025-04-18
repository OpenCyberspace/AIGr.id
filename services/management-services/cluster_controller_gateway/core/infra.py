import threading
from .infra_automation.infra_creator import create_cluster_infra, remove_cluster_infra
from .cluster_db import ClusterClient
from .global_tasks_db import GlobalTasksDB


class K8sControllerInfra:
    def __init__(self, cluster_id: str, kube_config_data: dict) -> None:
        self.cluster_id = cluster_id
        self.kube_config_data = kube_config_data
        self.cluster_client = ClusterClient()

    def create(self):
        try:
            success, cluster_data = self.cluster_client.read_cluster(
                self.cluster_id)
            if not success:
                raise RuntimeError(
                    f"Failed to read cluster data: {cluster_data}")

            global_url_map = create_cluster_infra(
                kube_config_data=self.kube_config_data,
                cluster_id=self.cluster_id,
                cluster_data=cluster_data
            )

            update_success, update_response = self.cluster_client.update_cluster(
                self.cluster_id, {"$set": {"config.urlMap": global_url_map}}
            )
            if not update_success:
                raise RuntimeError(
                    f"Failed to update cluster URL map: {update_response}")

            return update_response
        except Exception as e:
            raise e

    def remove(self):
        try:
            success, cluster_data = self.cluster_client.read_cluster(
                self.cluster_id)
            if not success:
                raise RuntimeError(
                    f"Failed to read cluster data: {cluster_data}")

            remove_cluster_infra(
                kube_config_data=self.kube_config_data,
                cluster_id=self.cluster_id,
                cluster_data=cluster_data
            )

            update_success, update_response = self.cluster_client.update_cluster(
                self.cluster_id, {"$set": {"config.urlMap": {}}}
            )
            if not update_success:
                raise RuntimeError(
                    f"Failed to clear cluster URL map: {update_response}")

            return update_response
        except Exception as e:
            raise e


class K8sInfraCreateTaskHandler:

    def __init__(self, cluster_id: str, kube_config_data: dict) -> None:
        self.cluster_id = cluster_id
        self.kube_config_data = kube_config_data

    def create_task(self):
        try:
            tasks_client = GlobalTasksDB()
            id = tasks_client.create_task(task_type="cluster_infra_creation", task_data={
                                          "cluster_id": self.cluster_id}, task_status="pending")
            return id
        except Exception as e:
            raise e

    def update_task(self, task_id, status, task_status_data):
        try:
            tasks_client = GlobalTasksDB()
            tasks_client.update_task(task_id, status, task_status_data)
        except Exception as e:
            raise e

    def create(self):
        task_id = self.create_task()

        def run():
            try:
                infra = K8sControllerInfra(
                    self.cluster_id, self.kube_config_data
                )
                result = infra.create()
                self.update_task(task_id, "completed", {"result": result})
            except Exception as e:
                self.update_task(task_id, "failed", {"error": str(e)})
        threading.Thread(target=run, daemon=True).start()
        return task_id

    def remove(self):
        task_id = self.create_task()

        def run():
            try:
                infra = K8sControllerInfra(
                    self.cluster_id, self.kube_config_data)
                result = infra.remove()
                self.update_task(task_id, "completed", {"result": result})
            except Exception as e:
                self.update_task(task_id, "failed", {"error": str(e)})
        threading.Thread(target=run, daemon=True).start()
        return task_id
