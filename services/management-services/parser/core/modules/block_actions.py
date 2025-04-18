import requests
import logging
import os


class BlockActionsClient:
    def __init__(self):
        self.base_url = os.getenv(
            "CLUSTER_CONTROLLER_GATEWAY_URL", "http://localhost:4000")
        self.logger = logging.getLogger(self.__class__.__name__)

    def _post_request(self, endpoint: str, payload: dict):
        url = f"{self.base_url}{endpoint}"
        self.logger.info(
            f"Sending POST request to {url} with payload: {payload}")

        try:
            response = requests.post(url, json=payload)

            if response.status_code == 200:
                self.logger.info(f"Successful response from {url}")
                return response.json()
            else:
                self.logger.error(
                    f"Request to {url} failed with status {response.status_code}: {response.text}"
                )
                return {"error": f"Request failed with status {response.status_code}: {response.text}"}
        except Exception as e:
            self.logger.exception(f"Exception during request to {url}: {e}")
            return {"error": str(e)}

    def select_clusters(self, payload: dict):
        self.logger.info("Calling select_clusters API")
        return self._post_request("/blockActions/selectClusters", payload)

    def allocate(self, payload: dict):
        self.logger.info("Calling allocate API")
        return self._post_request("/blockActions/allocate", payload)

    def dry_run(self, payload: dict):
        self.logger.info("Calling dry_run API")
        return self._post_request("/blockActions/dryRun", payload)


def execute_block_selection(ir: dict):
    try:

        actions = BlockActionsClient()
        return actions.select_clusters(ir)

    except Exception as e:
        raise e


def execute_block_allocation(ir: dict):
    try:
        actions = BlockActionsClient()
        return actions.allocate(ir)
    except Exception as e:
        raise e


def execute_vdag_allocation(ir: dict):
    try:
        actions = BlockActionsClient()
        return actions.allocate_vdag(ir)
    except Exception as e:
        raise e


def execute_cluster_dry_run(ir: dict):
    try:
        actions = BlockActionsClient()
        return actions.dry_run(ir)
    except Exception as e:
        raise e
