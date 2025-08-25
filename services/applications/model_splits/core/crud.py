import os
import logging
from pymongo import MongoClient, errors
from typing import List, Dict, Union, Tuple
from .torch_base import deploy_torch_local_cluster_ranks
from .k8s_objects_client import RemoteK8sExecutor
from .schema import SplitsDeploymentEntry  

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


class SplitsDeploymentDB:
    def __init__(self):
        try:
            uri = os.getenv("DB_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["splits"]
            self.collection = self.db["splits_deployments"]
            logger.info("MongoDB connection established for SplitsDeploymentDB")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, deployment: SplitsDeploymentEntry) -> Tuple[bool, Union[str, object]]:
        try:
            document = deployment.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"SplitsDeployment inserted: {deployment.deployment_name}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting SplitsDeployment: {e}")
            return False, str(e)

    def update(self, deployment_name: str, update_fields: Dict) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.update_one(
                {"deployment_name": deployment_name},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"SplitsDeployment {deployment_name} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document updated for {deployment_name}")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating SplitsDeployment: {e}")
            return False, str(e)

    def delete(self, deployment_name: str) -> Tuple[bool, Union[str, int]]:
        try:
            result = self.collection.delete_one({"deployment_name": deployment_name})
            if result.deleted_count > 0:
                logger.info(f"SplitsDeployment {deployment_name} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with deployment_name {deployment_name} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting SplitsDeployment: {e}")
            return False, str(e)

    def query(self, query_filter: Dict) -> Tuple[bool, Union[str, List[Dict]]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying SplitsDeployments: {e}")
            return False, str(e)

    def get_by_deployment_name(self, deployment_name: str) -> Tuple[bool, Union[str, SplitsDeploymentEntry]]:
        try:
            doc = self.collection.find_one({"deployment_name": deployment_name})
            if doc:
                doc.pop('_id', None)
                deployment = SplitsDeploymentEntry.from_dict(doc)
                logger.info(f"Retrieved SplitsDeployment: {deployment_name}")
                return True, deployment
            else:
                logger.info(f"No SplitsDeployment found with deployment_name: {deployment_name}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving SplitsDeployment: {e}")
            return False, str(e)



def create_splits_deployment(entry: SplitsDeploymentEntry):
    try:
        logger.info(f"Creating splits deployment: {entry.deployment_name}")

        # Save entry to DB
        db = SplitsDeploymentDB()
        success, result = db.insert(entry)
        if not success:
            raise Exception(f"Failed to store deployment entry: {result}")

        # Deploy pods and service
        if entry.platform == "torch":
            deploy_torch_local_cluster_ranks(
                cluster_id=entry.rank_0_cluster_id,  # For now assuming single cluster
                deployment_name=entry.deployment_name,
                nnodes=entry.nnodes,
                common_params=entry.common_params,
                per_rank_params=entry.per_rank_params,
                namespace=entry.namespace
            )
        else:
            raise Exception(f"Unsupported platform: {entry.platform}")

        logger.info(f"Deployment '{entry.deployment_name}' created successfully")

    except Exception as e:
        logger.error(f"Failed to create deployment '{entry.deployment_name}': {e}")
        raise


def remove_splits_deployment(deployment_name: str):
   
    try:
        logger.info(f"Removing splits deployment: {deployment_name}")

        db = SplitsDeploymentDB()
        success, result = db.get_by_deployment_name(deployment_name)
        if not success:
            raise Exception(f"Deployment not found: {result}")

        entry: SplitsDeploymentEntry = result
        executor = RemoteK8sExecutor(entry.cluster_id[0])  # assuming single cluster

        # Delete all pods
        pod_names = [f"{entry.deployment_name}-rank-{rank['rank']}" for rank in entry.per_rank_params]
        pod_specs = [{"kind": "Pod", "apiVersion": "v1", "metadata": {"name": name, "namespace": entry.namespace}} for name in pod_names]

        # Delete the service
        service_spec = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": f"{entry.deployment_name}-rank-master", "namespace": entry.namespace}
        }

        logger.info("Deleting service and pods from Kubernetes")
        executor.delete_objects_from_dicts([service_spec] + pod_specs)

        # Remove DB entry
        db.delete(deployment_name)

        logger.info(f"Deployment '{deployment_name}' removed successfully")

    except Exception as e:
        logger.error(f"Failed to remove deployment '{deployment_name}': {e}")
        raise
