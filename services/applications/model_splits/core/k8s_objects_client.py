import requests
import yaml
import os
import logging
from typing import List, Dict, Union

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class ClusterClient:
    def __init__(self):
        self.base_url = os.getenv(
            "CLUSTER_SERVICE_URL", "http://localhost:3000")

    def read_cluster(self, cluster_id):
        try:
            response = requests.get(f"{self.base_url}/clusters/{cluster_id}")
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as http_err:
            return False, f"HTTP error occurred: {http_err}"
        except Exception as err:
            return False, f"Error occurred: {err}"

    def get_cluster_controller_connection_url(self, cluster_id):
        try:
            ret, resp = self.read_cluster(cluster_id)

            if not ret:
                raise Exception(resp)

            config = resp["config"]

            if not 'urlMap' in config:
                raise Exception("config did not provide URL MAP")

            urlMap = config['urlMap']
            controller_url = urlMap.get("controllerService")

            return controller_url
        except Exception as e:
            raise e


class K8sObjectClient:
    def __init__(self, base_url: str):

        self.base_url = base_url.rstrip('/')

    def _post(self, endpoint: str, objects: List[Dict]):
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, json={"objects": objects})
        if not response.ok:
            raise Exception(f"[{response.status_code}] {response.text}")
        return response.json()

    def create_from_dicts(self, dicts: List[Dict]) -> Dict:

        return self._post("/cluster-actions/k8s-objects/create", dicts)

    def remove_from_dicts(self, dicts: List[Dict]) -> Dict:

        return self._post("/cluster-actions/k8s-objects/remove", dicts)

    def create_from_yaml_strings(self, yamls: List[str]) -> Dict:

        all_objects = []
        for yml in yamls:
            parsed = list(yaml.safe_load_all(yml))
            all_objects.extend([obj for obj in parsed if obj])
        return self._post("/cluster-actions/k8s-objects/create", all_objects)

    def remove_from_yaml_strings(self, yamls: List[str]) -> Dict:

        all_objects = []
        for yml in yamls:
            parsed = list(yaml.safe_load_all(yml))
            all_objects.extend([obj for obj in parsed if obj])
        return self._post("/cluster-actions/k8s-objects/remove", all_objects)


class RemoteK8sExecutor:
    def __init__(self, cluster_id: str):
        try:
            self.cluster_id = cluster_id
            self.cluster_client = ClusterClient()

            logger.info(f"Fetching controller URL for cluster: {cluster_id}")
            controller_url = self.cluster_client.get_cluster_controller_connection_url(
                cluster_id)

            if not controller_url:
                raise Exception(
                    "Controller URL not found in cluster configuration.")

            logger.info(f"Resolved controller URL: {controller_url}")
            self.k8s_client = K8sObjectClient(controller_url)

        except Exception as e:
            logger.error(
                f"Failed to initialize RemoteK8sExecutor for cluster {cluster_id}: {e}")
            raise

    def create_objects_from_dicts(self, resources: List[Dict]):
        try:
            logger.info(
                f"Creating {len(resources)} Kubernetes objects (dict mode) in cluster '{self.cluster_id}'")
            result = self.k8s_client.create_from_dicts(resources)
            logger.info(
                f"Successfully created objects in cluster '{self.cluster_id}'")
            return result
        except Exception as e:
            logger.error(f"Error creating objects from dicts: {e}")
            raise

    def delete_objects_from_dicts(self, resources: List[Dict]):
        try:
            logger.info(
                f"Deleting {len(resources)} Kubernetes objects (dict mode) in cluster '{self.cluster_id}'")
            result = self.k8s_client.remove_from_dicts(resources)
            logger.info(
                f"Successfully deleted objects in cluster '{self.cluster_id}'")
            return result
        except Exception as e:
            logger.error(f"Error deleting objects from dicts: {e}")
            raise

    def create_objects_from_yaml_strings(self, yamls: List[str]):
        try:
            logger.info(
                f"Creating Kubernetes objects from YAML (count: {len(yamls)}) in cluster '{self.cluster_id}'")
            result = self.k8s_client.create_from_yaml_strings(yamls)
            logger.info(
                f"Successfully created objects in cluster '{self.cluster_id}'")
            return result
        except Exception as e:
            logger.error(f"Error creating objects from YAML strings: {e}")
            raise

    def delete_objects_from_yaml_strings(self, yamls: List[str]):
        try:
            logger.info(
                f"Deleting Kubernetes objects from YAML (count: {len(yamls)}) in cluster '{self.cluster_id}'")
            result = self.k8s_client.remove_from_yaml_strings(yamls)
            logger.info(
                f"Successfully deleted objects in cluster '{self.cluster_id}'")
            return result
        except Exception as e:
            logger.error(f"Error deleting objects from YAML strings: {e}")
            raise
