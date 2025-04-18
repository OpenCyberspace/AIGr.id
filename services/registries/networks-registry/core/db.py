from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, List
from pymongo import MongoClient, errors
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class NetworkObject:
    network_id: str = ''
    network_name: str = ''
    metadata: Dict[str, Any] = field(default_factory=dict)
    services_map: Dict[str, str] = field(default_factory=dict)
    policies: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkObject':
        return cls(
            network_id=data.get('network_id', ''),
            network_name=data.get('network_name', ''),
            metadata=data.get('metadata', {}),
            services_map=data.get('services_map', {}),
            policies=data.get('policies', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'network_id': self.network_id,
            'network_name': self.network_name,
            'metadata': self.metadata,
            'services_map': self.services_map,
            'policies': self.policies
        }


class NetworkDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL")
            self.client = MongoClient(uri)
            self.db = self.client["vdags"]
            self.collection = self.db["networks"]
            logger.info("MongoDB connection established")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, network: NetworkObject) -> Tuple[bool, Any]:
        try:
            document = network.to_dict()
            result = self.collection.insert_one(document)
            logger.info(
                f"Network inserted with network_id: {network.network_id}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting network: {e}")
            return False, str(e)

    def update(self, network_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.update_one(
                {"network_id": network_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Network with network_id {network_id} updated")
                return True, result.modified_count
            else:
                logger.info(
                    f"No document found with network_id {network_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating network: {e}")
            return False, str(e)

    def delete(self, network_id: str) -> Tuple[bool, Any]:
        try:
            result = self.collection.delete_one({"network_id": network_id})
            if result.deleted_count > 0:
                logger.info(f"Network with network_id {network_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(
                    f"No document found with network_id {network_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting network: {e}")
            return False, str(e)

    def query(self, query_filter: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying networks: {e}")
            return False, str(e)

    def get_by_network_id(self, network_id: str) -> Tuple[bool, Any]:
        try:
            doc = self.collection.find_one({"network_id": network_id})
            if doc:
                doc.pop('_id', None)
                network = NetworkObject.from_dict(doc)
                logger.info(f"Network with network_id {network_id} retrieved")
                return True, network
            else:
                logger.info(f"No network found with network_id {network_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving network: {e}")
            return False, str(e)

