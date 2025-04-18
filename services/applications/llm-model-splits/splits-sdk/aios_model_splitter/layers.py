import requests
import os
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ModelLayerClient:
    def __init__(self):
        self.base_url = os.getenv("MODEL_LAYERS_REGISTRY_URL")

    def create_model_layer(self, payload: dict) -> dict:
        try:
            response = requests.post(f"{self.base_url}/model-layer", json=payload)
            response_data = response.json()
            if response_data.get("success"):
                return response_data["data"]
            raise Exception(response_data.get("error", "Unknown error during creation"))
        except Exception as e:
            logger.exception("Failed to create model layer")
            raise

    def get_model_layer(self, layer_hash: str) -> dict:
        try:
            response = requests.get(f"{self.base_url}/model-layer/{layer_hash}")
            response_data = response.json()
            if response_data.get("success"):
                return response_data["data"]
            raise Exception(response_data.get("error", "Layer not found"))
        except Exception as e:
            logger.exception("Failed to get model layer")
            raise

    def query_model_layers(self, query_filter: dict) -> list:
        try:
            response = requests.post(f"{self.base_url}/model-layers", json=query_filter)
            response_data = response.json()
            if response_data.get("success"):
                return response_data["data"]
            raise Exception(response_data.get("error", "Query failed"))
        except Exception as e:
            logger.exception("Failed to query model layers")
            raise
