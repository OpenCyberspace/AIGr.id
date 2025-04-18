from .arango import ArangoDBConnector

POLICY_DB_NAME = "aios-policies"

class PoliciesDB:

    @staticmethod
    def create_policy(
        policy_name="",
        policy_version="",
        iam_tokens=[],
        metadata={},
        tags=[],
        policy_code="",
        policy_type="",
        rule_uris="",
        policy_schema=None,
        policy_category="",
        release_tag="",
        db=None
    ) -> str:

        policy_uri = policy_category + "." + policy_name + ":" + policy_version + "-" + release_tag
        policy_object = {
            "_id": policy_uri,
            "name": policy_name,
            "version": policy_version,
            "iam_tokens": iam_tokens,
            "metadata": metadata,
            "tags": tags,
            "code": policy_code,
            "type": policy_type,
            "rule_uris": rule_uris,
            "policy_schema": policy_schema,
            "policy_category": policy_category,
            "release_tag": release_tag 
        }        

        try:
            collection = db.get_collection(POLICY_DB_NAME, "policies")
            collection.put(collection, policy_object)
            return policy_uri
        except Exception as e:
            raise e
    
    @staticmethod
    def get_policy_by_id(policy_uri: str, db=None):
        try:
            collection = db.get_collection(POLICY_DB_NAME, "policies")
            return db.get(collection, policy_uri)
        except Exception as e:
            raise e
    
    @staticmethod
    def get_policies(policy_uris = [], db = None):
        try:
            collection = db.get_collection(POLICY_DB_NAME, "policies")
            return db.get_entries(collection, policy_uris)
        except Exception as e:
            raise e
        
    @staticmethod
    def delete_policy(policy_uri=None, db=None):
        try:
            collection = db.get_collection(POLICY_DB_NAME, "policies")
            return db.remove(collection, policy_uri)
        except Exception as e:
            raise e
    
    @staticmethod
    def execute_aql(query_string, db=None, batch_size=100):
        try:
            return db.execute_aql(POLICY_DB_NAME, query_string, batch_size)
        except Exception as e:
            raise e