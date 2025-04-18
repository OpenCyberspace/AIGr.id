import os

from ..webhooks.component_registry import ComponentRegistryDB, ComponentRegistry
import random

from .aauth import ArangoDBConnector, ArangoAuth


class ConnectivityChecker:

    def __init__(self, parent_node_spec: dict, child_node_sepc: dict, op_name_parent: str, ip_name_child: str) -> None:
        self.parent_node_spec = parent_node_spec
        self.child_node_sepc = child_node_sepc
        self.db_auth_object = ArangoDBConnector(
            auth_object=ArangoAuth(
                host=os.getenv("POLICY_DB_ARANGO_HOST"),
                username=os.getenv("POLICY_DB_ARANGO_USERNAME"),
                password=os.getenv("POLICY_DB_ARANGO_PASSWORD"),
                options={}
            )
        )

        self.op_name_parent = op_name_parent
        self.ip_name_child = ip_name_child

    def check_connection(self):
        try:

            op_schema_parent_id = self.parent_node_spec["outputProtocol"][self.op_name_parent]
            ip_schema_child_id = self.child_node_sepc["inputProtocol"][self.ip_name_child]

            # get component registry info:
            ret, parent_component = ComponentRegistry.GetComponentByURI(
                op_schema_parent_id)
            if not ret:
                raise Exception(str(parent_component))

            ret, child_component = ComponentRegistry.GetComponentByURI(
                ip_schema_child_id)
            if not ret:
                raise Exception(str(child_component))

            # check base types:
            child_base = child_component['componentConfig']['schema']['baseType']
            parent_base = parent_component['componentConfig']['schema']['baseType']

            if child_base == parent_base:
                return True, {"match": True, "convertor_policy_rule": ""}

            # search for convertor policy-rule:
            query_expression = '''
                FOR x in aios_v1_policies
                    FILTER x.policy_category == "schema_convertors" &&
                           x.metadata.function_keys.input == {} &&
                           x.metadata.function_keys.output == {}
                    RETURN x._key
            '''.format(self.op_name_parent, self.ip_name_child)

            ret, results = self.db_auth_object.execute_aql(
                query_string=query_expression, db=self.db_auth_object)

            if not ret:
                raise Exception(str(results))

            if len(results) == 0:
                raise Exception(
                    "no convertor policy found between {} and {}",
                    self.op_name_parent, self.ip_name_child
                )

            selected_policy_rule = random.choice(results)

            return True, {"match": False, "convertor_policy_rule": selected_policy_rule}

        except Exception as e:
            raise e
