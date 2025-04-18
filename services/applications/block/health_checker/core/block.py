import requests


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
