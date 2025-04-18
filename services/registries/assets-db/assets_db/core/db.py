import os
from pymongo import MongoClient, errors
from typing import Tuple, Union, List, Dict
import logging
from .schema import AssetObject

logger = logging.getLogger(__name__)

class AssetStoreDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["assets"]
            self.collection = self.db["assets"]
            logger.info("MongoDB connection established for AssetStoreDatabase")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, asset: AssetObject) -> Tuple[bool, Union[str, None]]:
        try:
            document = asset.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Asset inserted with asset_uri: {asset.asset_uri}")
            return True, str(result.inserted_id)
        except errors.PyMongoError as e:
            logger.error(f"Error inserting asset: {e}")
            return False, str(e)

    def update(self, asset_uri: str, update_fields: Dict) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.update_one(
                {"asset_uri": asset_uri},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Asset with asset_uri {asset_uri} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with asset_uri {asset_uri} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating asset: {e}")
            return False, str(e)

    def delete(self, asset_uri: str) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.delete_one({"asset_uri": asset_uri})
            if result.deleted_count > 0:
                logger.info(f"Asset with asset_uri {asset_uri} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with asset_uri {asset_uri} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting asset: {e}")
            return False, str(e)

    def query(self, query_filter: Dict) -> Tuple[bool, Union[List[Dict], str]]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying assets: {e}")
            return False, str(e)

    def get_by_asset_uri(self, asset_uri: str) -> Tuple[bool, Union[AssetObject, str]]:
        try:
            doc = self.collection.find_one({"asset_uri": asset_uri})
            if doc:
                doc.pop('_id', None)
                asset = AssetObject.from_dict(doc)
                logger.info(f"Asset with asset_uri {asset_uri} retrieved")
                return True, asset
            else:
                logger.info(f"No asset found with asset_uri {asset_uri}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving asset: {e}")
            return False, str(e)
