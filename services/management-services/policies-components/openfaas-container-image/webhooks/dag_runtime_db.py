import requests
import os

DAG_RUNTIME_DB_API = os.getenv("DAG_RUNTIME_DB_API")


class DB_API:

    @staticmethod
    def mk_query(payload, route):
        try:
            URL = DAG_RUNTIME_DB_API + route
            response = requests.post(URL, json=payload)
            if response.status_code != 200:
                raise Exception(
                    "Server error, failed to make Request code={}".format(
                        response.status_code
                    )
                )

            data = response.json()
            if data['error']:
                raise Exception(data['message'])

            return True, data['payload']

        except Exception as e:
            return False, e

    @staticmethod
    def get_node(nodeType: str, queryData: dict):
        return DB_API.mk_query(
            {"nodeType": nodeType, "query": [queryData]},
            "/queryVertex"
        )

    @staticmethod
    def get_child(parentNodeType, parentQuery,
                  childNodeType, childQuery, relName):

        return DB_API.mk_query(
            payload={
                "parent": {
                    "nodeType": parentNodeType,
                    "query": parentQuery
                },
                "child": {
                    "nodeType": childNodeType,
                    "query": childQuery
                },
                "relation": relName
            },
            route="/getChildren"
        )

    @staticmethod
    def get_parents(parentNodeType, parentQuery,
                    childNodeType, childQuery, relName):

        return DB_API.mk_query(
            payload={
                "parent": {
                    "nodeType": parentNodeType,
                    "query": parentQuery
                },
                "child": {
                    "nodeType": childNodeType,
                    "query": childQuery
                },
                "relation": relName
            },
            route="/getParents"
        )

    @staticmethod
    def add_vertex(nodeType, data):
        return DB_API.mk_query(
            payload={
                "nodeType": nodeType,
                "data": data
            },
            route="/addVertex"
        )

    @staticmethod
    def add_child(parentNodeType, parentQuery, relName,
                  childNodeType, childData):

        return DB_API.mk_query(
            payload={
                "parent": {
                    "nodeType": parentNodeType,
                    "query": parentQuery
                },
                "relation": relName,
                "child": {
                    "nodeType": childNodeType,
                    "data": childData
                }
            },
            route="/addChildVertex"
        )

    @staticmethod
    def link_nodes(v1Type, v1Query, v2Type, v2Query, relName):
        return DB_API.mk_query(
            payload={
                "v1": {
                    "nodeType": v1Type,
                    "query": v1Query
                },
                "v2": {
                    "nodeType": v2Type,
                    "query": v2Query
                },
                "relation": relName
            },
            route="/createEdge"
        )

    @staticmethod
    def update_vertex(vertexID, data):
        return DB_API.mk_query(
            payload={
                "vertexID": vertexID,
                "data": data
            },
            route="/updateVertex"
        )

    @staticmethod
    def update_by_v_id(v_id, data):
        return DB_API.mk_query(
            payload={
                "vertexID": v_id,
                "data": data
            },
            route="/updateVertex"
        )

    @staticmethod
    def bulk_delete(nodes):
        return DB_API.mk_query(
            payload={
                "idList": nodes
            },
            route="/bulkDelete"
        )
