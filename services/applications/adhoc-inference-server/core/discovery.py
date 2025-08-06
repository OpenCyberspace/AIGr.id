import requests
import os
import redis
import json
import logging

from .search import map_block_to_search


class BlocksDB:
    def __init__(self, base_url):
        self.base_url = base_url

    def create_block(self, data):
        try:
            response = requests.post(f'{self.base_url}/blocks', json=data)
            if response.status_code != 200:
                raise Exception("API returned non-200 status code")
            return True, response.json()
        except Exception as e:
            return False, str(e)

    def get_all_blocks(self):
        try:
            response = requests.get(f'{self.base_url}/blocks')
            if response.status_code != 200:
                raise Exception("API returned non-200 status code")
            return True, response.json()
        except Exception as e:
            return False, str(e)

    def get_block_by_id(self, block_id):
        try:
            response = requests.get(f'{self.base_url}/blocks/{block_id}')
            if response.status_code != 200:
                raise Exception("API returned non-200 status code")
            return True, response.json()
        except Exception as e:
            return False, str(e)

    def update_block_by_id(self, block_id, data):
        try:
            response = requests.put(
                f'{self.base_url}/blocks/{block_id}', json=data)
            if response.status_code != 200:
                raise Exception("API returned non-200 status code")
            return True, response.json()
        except Exception as e:
            return False, str(e)

    def delete_block_by_id(self, block_id):
        try:
            response = requests.delete(f'{self.base_url}/blocks/{block_id}')
            if response.status_code != 200:
                raise Exception("API returned non-200 status code")
            return True, response.json()
        except Exception as e:
            return False, str(e)

    def query_blocks(self, query_params):
        try:
            response = requests.post(
                f'{self.base_url}/blocks/query', json=query_params)
            if response.status_code != 200:
                raise Exception("API returned non-200 status code")
            return True, response.json()
        except Exception as e:
            return False, str(e)


class ClustersDB:
    def __init__(self, base_url):
        self.base_url = base_url

    def create_cluster(self, data):
        try:
            response = requests.post(f'{self.base_url}/clusters', json=data)
            if response.status_code != 201:
                raise Exception("API returned non-201 status code")
            return True, response.json()
        except Exception as e:
            return False, str(e)

    def get_cluster_by_id(self, cluster_id):
        try:
            response = requests.get(f'{self.base_url}/clusters/{cluster_id}')
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 404:
                raise Exception("Cluster not found")
            else:
                raise Exception("API returned non-200/404 status code")
        except Exception as e:
            return False, str(e)

    def update_cluster_by_id(self, cluster_id, data):
        try:
            response = requests.put(
                f'{self.base_url}/clusters/{cluster_id}', json=data)
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 404:
                raise Exception("Cluster not found")
            else:
                raise Exception("API returned non-200/404 status code")
        except Exception as e:
            return False, str(e)

    def delete_cluster_by_id(self, cluster_id):
        try:
            response = requests.delete(
                f'{self.base_url}/clusters/{cluster_id}')
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 404:
                raise Exception("Cluster not found")
            else:
                raise Exception("API returned non-200/404 status code")
        except Exception as e:
            return False, str(e)

    def query_clusters(self, query):
        try:
            response = requests.post(
                f'{self.base_url}/clusters/query', json={"query": query})
            if response.status_code != 200:
                raise Exception("API returned non-200 status code")
            return True, response.json()
        except Exception as e:
            return False, str(e)


class ConnectionsCache:
    def __init__(self):
        self.connections = {}

    def get_connection(self, url: str) -> redis.Redis:
        if url in self.connections:
            return self.connections[url]
        else:
            new_connection = redis.Redis(
                host=url, port=6379, db=0, password=None)
            self.connections[url] = new_connection
            return new_connection


class DiscoveryCache:

    def __init__(self) -> None:
        self.entries = {}
        self.discovery_mode = os.getenv("DISCOVERY_MODE", "gateway")
        self.cluster_id = os.getenv("CLUSTER_ID", "default-cluster")

    def __discover(self, block_id):
        try:

            block_db = BlocksDB(
                os.getenv("BLOCKS_DB_URL", "c"))
            ret, block = block_db.get_block_by_id(block_id)

            if not ret:
                raise Exception(f"{block_id} not found in the DB, err={block}")

            cluster_id = block['cluster'].get('id', '')
            if cluster_id == "":
                raise Exception(
                    f"cluster is not defined for the block {cluster_id}"
                )

            cluster_data = block['cluster']

            cluster_id = cluster_data['id']

            config = cluster_data['config']['urlMap']
            public_gateway_url = config.get('publicGateway', '')

            if type(public_gateway_url) == list and len(public_gateway_url) > 0:
                public_gateway_url = public_gateway_url[0]

            if public_gateway_url == '':
                raise Exception(
                    f"cluster did not define the public gateway url: {public_gateway_url}"
                )

            logging.info(f"block_id:{block_id} --> cluster:{cluster_id},gateway:{public_gateway_url}")

            return public_gateway_url, cluster_id

        except Exception as e:
            raise e

    def discover(self, block_id, instance_id=""):
        try:

            key = ""
            if instance_id != "":
                key = f"{block_id}-{instance_id}"
            else:
                key = block_id

            # discover from the cache:
            if key in self.entries:
                access_address, port = self.entries[key]
                return access_address, port

            if self.discovery_mode == "gateway":
                # discover internally:
                public_url, cluster_id = self.__discover(block_id)

                if self.cluster_id == cluster_id:
                    local_url = f"{block_id}-executor-svc.blocks.svc.cluster.local"
                    self.entries[key] = (local_url, 6379)
                    return local_url, 6379

                self.entries[key] = (public_url, 0)
                return public_url, 0
            else:
                if instance_id == "":
                    return os.getenv("QUEUE_DEFAULT_URL", "localhost:50051"), None
                else:
                    return os.getenv("QUEUE_DEFAULT_URL", "localhost:50051"), None

        except Exception as e:
            raise e


class GraphCache:

    def __init__(self) -> None:
        self.items = {}
        self.block_db = BlocksDB(
            os.getenv("BLOCKS_DB_URL", "http://localhost:3001"))

    def get(self, block_id: str):
        try:

            if block_id in self.items:
                return self.items[block_id]

            ret, block = self.block_db.get_block_by_id(block_id)
            if not ret:
                raise Exception(f"block with ID {block_id} not found")

            cluster = block['cluster']
            config = cluster.get('config', {}).get('urlMap', {})

            public_url = config.get('publicGateway', '')

            if len(public_url) == 0:
                raise Exception("Public gateway URL not defined")

            if type(public_url) == list and len(public_url) > 0:
                public_url = public_url[0]
            

            local_url = f"{block_id}-executor-svc.blocks.svc.cluster.local"
            item = {
                "local": local_url,
                "public": public_url,
                "clusterId": cluster['id']
            }

            self.items[block_id] = item

            return item

        except Exception as e:
            raise e

    def resolve_outputs(self, parent_block, child_blocks_list):
        try:

            parent = self.get(parent_block)
            child_blocks = {}
            for block_id in child_blocks_list:
                child_blocks[block_id] = self.get(block_id)

            # resolve node connections now:
            blk_output = {
                "outputs": []
            }

            for blk_id, child in child_blocks.items():
                is_same_cluster = child['clusterId'] == parent['clusterId']
                blk_output["outputs"].append({
                    "host": child['local'] if is_same_cluster else child['public'],
                    "port": 6379 if is_same_cluster else 0,
                    "queue_name": "EXECUTOR_INPUTS",
                    "block_id": blk_id
                })

            return blk_output

        except Exception as e:
            raise e


class SearchSessionsCache:

    def __init__(self) -> None:
        self.sessions = {}
        self.discovery_mode = os.getenv("DISCOVERY_MODE", "gateway")

    def get_block_id(self, session_id: str, search_data: str):
        try:

            if self.discovery_mode == "testing":
                return os.getenv("INSTANCE_BLOCK_DEFAULT_URL", "localhost")
            else:
                # handle gateway:
                if session_id in self.sessions:
                    return self.sessions[session_id]

                # handle new connection:
                search_response = map_block_to_search(search_data)
                block_id = search_response.get('id', '')
                if block_id == "":
                    raise Exception(
                        f"invalid similarity search result, {search_response}")

                self.sessions[session_id] = block_id
                return block_id

        except Exception as e:
            raise e


class MgmtAPIClient:
    def __init__(self, base_url="http://localhost:18001"):
        self.base_url = base_url

    def send_request(self, mgmt_action, mgmt_data=None):
        url = f"{self.base_url}/"
        payload = {"mgmt_action": mgmt_action}
        if mgmt_data:
            payload["mgmt_data"] = mgmt_data

        try:
            response = requests.post(url, json=payload)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("success"):
                return response_data.get("data")
            else:
                raise Exception(response_data.get("message", "Unknown error"))
        except requests.RequestException as e:
            raise Exception(f"Request error: {str(e)}")
        except ValueError:
            raise Exception("Invalid JSON response from server")

    def estimate(self):
        return self.send_request("estimate")

    def check_execute(self, mgmt_data):
        if not isinstance(mgmt_data, dict):
            raise ValueError("mgmt_data must be a dictionary")
        return self.send_request("check_execute", mgmt_data)


class Estimator:

    def __call__(self):
        self.graph_cache = GraphCache()

    def estimate(self, search_query: dict, block_id: str):
        try:

            if search_query:
                blocks = map_block_to_search(json.dumps(search_query))
                for block in blocks:
                    connection = self.graph_cache.get(block['id'])
                    url = connection['host']
                    url = url + "/mgmt"
                    response = MgmtAPIClient(url).estimate()
                    return response['data']
            else:
                connection = self.graph_cache.get(block_id)
                url = connection['host']
                url = url + "/mgmt"
                response = MgmtAPIClient(url).estimate()
                return response['data']

        except Exception as e:
            raise e

    def check_execute(self, search_query: dict, query_params: dict, block_id: str):
        try:

            if search_query:
                blocks = map_block_to_search(json.dumps(search_query))
                for block in blocks:
                    connection = self.graph_cache.get(block['id'])
                    url = connection['host']
                    url = url + "/mgmt"
                    response = MgmtAPIClient(url).check_execute(query_params)
                    return response['data']
            else:
                connection = self.graph_cache.get(block_id)
                url = connection['host']
                url = url + "/mgmt"
                response = MgmtAPIClient(url).estimate()
                return response['data']

        except Exception as e:
            raise e
