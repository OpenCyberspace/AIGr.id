import os
import logging
from pymongo import MongoClient, errors
from typing import Dict, List, Tuple, Union
from .schema import TemplateObject

logger = logging.getLogger(__name__)

class TemplateStoreDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["templates"]
            self.collection = self.db["templates"]
            logger.info("MongoDB connection established for TemplateStoreDatabase")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, template: TemplateObject) -> Tuple[bool, Union[str, None]]:
        try:
            document = template.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"Template inserted with templateUri: {template.templateUri}")
            return True, str(result.inserted_id)
        except errors.PyMongoError as e:
            logger.error(f"Error inserting template: {e}")
            return False, str(e)

    def update(self, templateUri: str, update_fields: Dict) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.update_one(
                {"templateUri": templateUri},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"Template with templateUri {templateUri} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with templateUri {templateUri} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating template: {e}")
            return False, str(e)

    def delete(self, templateUri: str) -> Tuple[bool, Union[int, str]]:
        try:
            result = self.collection.delete_one({"templateUri": templateUri})
            if result.deleted_count > 0:
                logger.info(f"Template with templateUri {templateUri} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with templateUri {templateUri} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting template: {e}")
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
            logger.error(f"Error querying templates: {e}")
            return False, str(e)

    def get_by_templateUri(self, templateUri: str) -> Tuple[bool, Union[TemplateObject, str]]:
        try:
            doc = self.collection.find_one({"templateUri": templateUri})
            if doc:
                doc.pop('_id', None)
                template = TemplateObject.from_dict(doc)
                logger.info(f"Template with templateUri {templateUri} retrieved")
                return True, template
            else:
                logger.info(f"No template found with templateUri {templateUri}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving template: {e}")
            return False, str(e)
