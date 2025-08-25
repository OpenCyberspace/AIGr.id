import requests
import json
import logging
import os

from .cluster_db import ClusterClient


class ClusterControllerExecutor:

    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def execute_action(self, action, payload):
        url = f"{self.base_url}/executeAction"
        payload['action'] = action
        payload['cluster_id'] = os.getenv("CLUSTER_ID")

        logging.info('sending payload: data={} to={}'.format(payload, url))

        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(
                url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            self.logger.info(f"Response: {response.json()}")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            self.logger.error(f"HTTP error occurred: {http_err}")
            return {"success": False, "data": f"HTTP error occurred: {http_err}"}
        except Exception as err:
            self.logger.error(f"Other error occurred: {err}")
            return {"success": False, "data": f"Other error occurred: {err}"}

    def remove_block(self, payload):
        return self.execute_action("remove_block", payload)

    def create_block(self, payload):
        return self.execute_action("create_block", payload)

    def parameter_update(self, payload):
        return self.execute_action("parameter_update", payload)

    def scale_instance(self, payload):
        return self.execute_action("scale", payload)

    def remove_instance(self, payload):
        return self.execute_action("remove_instance", payload)

    def resource_allocation(self, payload):
        return self.execute_action("create_block", payload)

    def dry_run(self, payload):
        return self.execute_action("dry_run", payload)
    
    def init_create_status_update(self, payload):
        return self.execute_action("init_create_status_update", payload)

    def query_init_container_data(self, payload):
        return self.execute_action("query_init_container_data", payload)

    def reassign(self, payload):
        return self.execute_action("reassign", payload)


def get_cluster_controller_connection(cluster_id):
    try:

        cluster_client = ClusterClient()
        ret, resp = cluster_client.read_cluster(cluster_id)

        if not ret:
            raise Exception(resp)

        config = resp["config"]

        if not 'urlMap' in config:
            raise Exception("config did not provide URL MAP")

        urlMap = config['urlMap']
        service_url = urlMap.get("controllerService")

        logging.info("cluster url: {}".format(service_url))

        return ClusterControllerExecutor(base_url=service_url)

    except Exception as e:
        raise e

def get_cluster_controller_connection_url(cluster_id):
    try:

        cluster_client = ClusterClient()
        ret, resp = cluster_client.read_cluster(cluster_id)

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

def get_cluster_mgmt_connection_url(cluster_id):
    try:

        cluster_client = ClusterClient()
        ret, resp = cluster_client.read_cluster(cluster_id)

        if not ret:
            raise Exception(resp)

        config = resp["config"]

        if not 'urlMap' in config:
            raise Exception("config did not provide URL MAP")

        urlMap = config['urlMap']
        controller_url = urlMap.get("parameterUpdater")

        return controller_url

    except Exception as e:
        raise e


def get_cluster_controller_connection_from_doc(cluster):
    try:


        config = cluster["config"]

        if not 'urlMap' in config:
            raise Exception("config did not provide URL MAP")

        urlMap = config['urlMap']
        controller_url = urlMap.get("controllerService")

        logging.info('controller url: {}'.format(controller_url))

        return controller_url

    except Exception as e:
        raise e


def get_cluster_membership_connection_url(cluster_id):
    try:

        cluster_client = ClusterClient()
        ret, resp = cluster_client.read_cluster(cluster_id)

        if not ret:
            raise Exception(resp)

        config = resp["config"]

        if not 'urlMap' in config:
            raise Exception("config did not provide URL MAP")

        urlMap = config['urlMap']
        controller_url = urlMap.get("membershipServer")

        return controller_url

    except Exception as e:
        raise e