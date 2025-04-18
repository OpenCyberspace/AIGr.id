
POLICY_DB_NAME = "aios-policies"


class RulesDB:

    @staticmethod
    def create_rule(
        rule_name="",
        rule_version="",
        iam_tokens=[],
        metadata={},
        tags=[],
        rule_code="",
        rule_type="",
        policy_uris="",
        rule_schema=None,
        rule_category="",
        release_tag="",
        db=None
    ) -> str:

        rule_uri = rule_category + "." + rule_name + \
            ":" + rule_version + "-" + release_tag
        rule_object = {
            "_id": rule_uri,
            "name": rule_name,
            "version": rule_version,
            "iam_tokens": iam_tokens,
            "metadata": metadata,
            "tags": tags,
            "code": rule_code,
            "type": rule_type,
            "policy_uris": policy_uris,
            "rule_schema": rule_schema,
            "rule_category": rule_category,
            "release_tag": release_tag
        }

        try:
            collection = db.get_collection(POLICY_DB_NAME, "rules")
            collection.put(collection, rule_object)
            return rule_uri
        except Exception as e:
            raise e

    @staticmethod
    def get_rule_by_id(rule_uri: str, db=None):
        try:
            collection = db.get_collection(POLICY_DB_NAME, "rules")
            return db.get(collection, rule_uri)
        except Exception as e:
            raise e

    @staticmethod
    def get_rules(rule_uris=[], db=None):
        try:
            collection = db.get_collection(POLICY_DB_NAME, "rules")
            return db.get_entries(collection, rule_uris)
        except Exception as e:
            raise e

    @staticmethod
    def delete_rule(rule_uri=None, db=None):
        try:
            collection = db.get_collection(POLICY_DB_NAME, "rules")
            return db.remove(collection, rule_uri)
        except Exception as e:
            raise e

    @staticmethod
    def execute_aql(query_string, db=None, batch_size=100):
        try:
            return db.execute_aql(POLICY_DB_NAME, query_string, batch_size)
        except Exception as e:
            raise e
