import uuid


MAPPING_DB_NAME = "infra-mapping"


class BlocksMapping:

    @staticmethod
    def create_mapping(
        rule_uri=None,
        config_set=None,
        mdag_id=None,
        cluster_dag_id=None,
        scale_layout_block_id=None,
        rule_type=None,
        allocation_info=None,
        db=None,
    ) -> str:

        _id = uuid.uuid4()
        rule_object = {
            "_id": _id,
            "rule_uri": rule_uri,
            "config_set": config_set,
            "mdag_id": mdag_id,
            "cluster_dag_id": cluster_dag_id,
            "scale_layout_block_id": scale_layout_block_id,
            "rule_type": rule_type,
            "allocation_info": allocation_info,
        }

        try:
            collection = db.get_collection(MAPPING_DB_NAME, "block-mapping")
            collection.put(collection, rule_object)
            return rule_uri
        except Exception as e:
            raise e

    @staticmethod
    def get_mapping_by_uri(rule_uri: str, db=None):
        try:
            collection = db.get_collection(MAPPING_DB_NAME, "block-mapping")
            return db.get(collection, rule_uri)
        except Exception as e:
            raise e

    @staticmethod
    def get_mappings(rule_uris=[], db=None):
        try:
            collection = db.get_collection(MAPPING_DB_NAME, "block-mapping")
            return db.get_entries(collection, rule_uris)
        except Exception as e:
            raise e

    @staticmethod
    def delete_mapping(rule_uri=None, db=None):
        try:
            collection = db.get_collection(MAPPING_DB_NAME, "block-mapping")
            return db.remove(collection, rule_uri)
        except Exception as e:
            raise e

    @staticmethod
    def execute_aql(query_string, db=None, batch_size=100):
        try:
            return db.execute_aql(MAPPING_DB_NAME, query_string, batch_size)
        except Exception as e:
            raise e
