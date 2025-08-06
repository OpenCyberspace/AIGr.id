import logging
import yaml
from typing import List, Union, Dict
from kubernetes import client, config, utils
from kubernetes.dynamic import DynamicClient
from kubernetes.config.config_exception import ConfigException

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

class KubernetesInterface:
    def __init__(self):
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration.")
        except ConfigException:
            try:
                config.load_kube_config()
                logger.info("Loaded local kubeconfig.")
            except Exception as e:
                logger.error(f"Failed to load any Kubernetes config: {e}")
                raise

        try:
            self.api_client = client.ApiClient()
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes API client: {e}")
            raise

    def create_resources(self, resources: List[Union[str, Dict]]):
        
        for item in resources:
            try:
                yaml_docs = self._parse_input(item)

                for doc in yaml_docs:
                    if not doc:
                        continue
                    utils.create_from_dict(self.api_client, data=doc)
                    kind = doc.get("kind", "<unknown>")
                    name = doc.get("metadata", {}).get("name", "<unnamed>")
                    logger.info(f"Created {kind} '{name}'")
            except Exception as e:
                logger.error(f"Failed to create resource from input: {e}")
                raise

    def delete_resources(self, resources: List[Union[str, Dict]]):
    
        for item in resources:
            try:
                yaml_docs = self._parse_input(item)

                for doc in yaml_docs:
                    if not doc:
                        continue

                    api_version = doc.get("apiVersion")
                    kind = doc.get("kind")
                    metadata = doc.get("metadata", {})
                    name = metadata.get("name")
                    namespace = metadata.get("namespace", "default")

                    if not api_version or not kind or not name:
                        logger.warning(f"Incomplete resource definition: {doc}")
                        continue

                    try:
                        dyn_client = DynamicClient(self.api_client)
                        dyn_resource = dyn_client.resources.get(api_version=api_version, kind=kind)
                        dyn_resource.delete(name=name, namespace=namespace)
                        logger.info(f"Deleted {kind} '{name}' from namespace '{namespace}'")
                    except Exception as inner_e:
                        logger.error(f"Failed to delete {kind} '{name}': {inner_e}")
                        raise

            except Exception as e:
                logger.error(f"Failed to parse/delete resource from input: {e}")
                raise

    def _parse_input(self, item: Union[str, Dict]) -> List[Dict]:
     
        if isinstance(item, dict):
            return [item]
        elif isinstance(item, str):
            try:
                return list(yaml.safe_load_all(item))
            except yaml.YAMLError as e:
                logger.error(f"YAML parsing error: {e}")
                raise
        else:
            raise ValueError(f"Unsupported input type: {type(item)}")
