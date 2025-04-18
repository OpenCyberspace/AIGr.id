import os
from .webhooks.blocks import BlocksClient
from .policy_sandbox import LocalPolicyEvaluator
from .webhooks.clusters import ClusterClient
from .webhooks.global_metrics import GlobalBlocksMetricsClient, GlobalClusterMetricsClient
from .webhooks.component_registry import ComponentRegistryDB
from .webhooks.vdag import vDAGsClient
from .webhooks.policies import PoliciesQueryClient
from .webhooks.vdag_metrics import vDAGMetricsQuery

def query_translator(query):
    def translate_condition(condition):
        if "logicalOperator" in condition:
            return translate_logical_operator(condition)
        else:
            return translate_simple_condition(condition)

    def translate_simple_condition(condition):
        variable = condition["variable"]
        operator = condition["operator"]
        value = condition["value"]

        if operator == "LIKE":
            # MongoDB uses regex for LIKE operations
            regex_value = value.replace(".", r"\.").replace("*", ".*")
            return {variable: {"$regex": regex_value}}
        elif operator == "==":
            return {variable: value}
        elif operator == "IN":
            return {variable: {"$in": value}}
        elif operator == "<":
            return {variable: {"$lt": value}}
        elif operator == "<=":
            return {variable: {"$lte": value}}
        elif operator == ">":
            return {variable: {"$gt": value}}
        elif operator == ">=":
            return {variable: {"$gte": value}}
        else:
            raise ValueError(f"Unsupported operator: {operator}")

    def translate_logical_operator(condition):
        logical_operator = condition["logicalOperator"]
        sub_conditions = condition["conditions"]
        translated_conditions = [translate_condition(
            cond) for cond in sub_conditions]

        if logical_operator == "AND":
            return {"$and": translated_conditions}
        elif logical_operator == "OR":
            return {"$or": translated_conditions}
        else:
            raise ValueError(
                f"Unsupported logical operator: {logical_operator}")

    return translate_condition(query)


def execute_query(entity_type, query):
    try:

        db_query = query_translator(query)
        print('db query', db_query)

        if entity_type == "component":
            resp = ComponentRegistryDB().query(db_query)
            return True, resp

        if entity_type == "cluster":
            return ClusterClient().execute_query(db_query)
        if entity_type == "block":
            resp = BlocksClient().query_blocks(db_query)
            return True, resp

        if entity_type == "clusterMetrics":
            resp = GlobalClusterMetricsClient().query_clusters(db_query)
            print(f'cluster metrics query: {resp}')
            return True, resp

        if entity_type == "blockMetrics":
            resp = GlobalBlocksMetricsClient().query_blocks(db_query)
            return True, resp

        if entity_type == "vdag":
            resp = vDAGsClient().query_vdags(db_query)
            return True, resp

        if entity_type == "policy":
            resp = PoliciesQueryClient().query_policies(db_query)
            return True, resp

        if entity_type == "policyFunction":
            resp = PoliciesQueryClient().query_functions(db_query)
            return True, resp

        if entity_type == "policyGraph":
            resp = PoliciesQueryClient().query_graphs(db_query)
            return True, resp

        if entity_type == "vdagMetrics":
            resp = vDAGMetricsQuery()
            resp.query(db_query)

        raise Exception("unknown query type")

    except Exception as e:
        raise e


def execute_filter(filter_type, query):
    try:

        if filter_type == "component":
            _, components = execute_query("component", query['componentQuery'])
            return components

        if filter_type == "block":
            # check if the query has cluster_query:
            if 'clusterQuery' in query:
                _, clusters = execute_query("cluster", query['clusterQuery'])
                if len(clusters) == 0:
                    return None
                ids = [cluster['id'] for cluster in clusters]

                if ('blockQuery' not in query) or len(query['blockQuery']) == 0:
                    query['blockQuery'] = {
                        "variable": "cluster.id",
                        "operator": "IN",
                        "value": ids
                    }
                elif 'conditions' in query['blockQuery']:

                    query['blockQuery']['conditions'].append({
                        "variable": "cluster.id",
                        "operator": "IN",
                        "value": ids
                    })
                elif 'variable' in query['blockQuery']:
                    query['blockQuery'] = {
                        "logicalOperator": "AND",
                        "conditions": [query['blockQuery'], {
                            "variable": "cluster.id",
                            "operator": "IN",
                            "value": ids
                        }]
                    }

            if 'blockMetricsQuery' in query:
                _, blocks = execute_query(
                    "blockMetrics", query['blockMetricsQuery'])
                # add block metrics to the query entries:
                ids = [block['blockId'] for block in blocks]

                if ('blockQuery' not in query) or len(query['blockQuery']) == 0:
                    query['blockQuery'] = {
                        "variable": "id",
                        "operator": "IN",
                        "value": ids
                    }
                elif 'conditions' in query['blockQuery']:

                    query['blockQuery']['conditions'].append({
                        "variable": "id",
                        "operator": "IN",
                        "value": ids
                    })
                elif 'variable' in query['blockQuery']:
                    query['blockQuery'] = {
                        "logicalOperator": "AND",
                        "conditions": [query['blockQuery'], {
                            "variable": "id",
                            "operator": "IN",
                            "value": ids
                        }]
                    }

            _, blocks = execute_query(filter_type, query['blockQuery'])
            return blocks

        if filter_type == "cluster":

            if 'clusterMetricsQuery' in query:
                _, metricClusters = execute_query(
                    "clusterMetrics", query['clusterMetricsQuery'])
                if len(metricClusters) == 0:
                    return None

                ids = [metricCluster['clusterId']
                       for metricCluster in metricClusters]

                # prepare query:
                if ('clusterQuery' not in query) or len(query['clusterQuery']) == 0:
                    query['clusterQuery'] = {
                        "variable": "id",
                        "operator": "IN",
                        "value": ids
                    }
                elif 'conditions' in query['clusterQuery']:

                    query['clusterQuery']['conditions'].append({
                        "variable": "id",
                        "operator": "IN",
                        "value": ids
                    })
                elif 'variable' in query['clusterQuery']:
                    query['clusterQuery'] = {
                        "logicalOperator": "AND",
                        "conditions": [query['clusterQuery'], {
                            "variable": "id",
                            "operator": "IN",
                            "value": ids
                        }]
                    }

            _, clusters = execute_query(filter_type, query['clusterQuery'])
            return clusters

        if filter_type == "vdag":

            if 'vdagMetricsQuery' in query:
                _, metricsvDAGs = execute_query('vdagMetrics', query['vdagMetrics'])
                if len(metricsvDAGs) == 0:
                    return None
                
                ids = [metrics['vdagURI'] for metrics in metricsvDAGs]
                if ('vdagQuery' not in query) or len(query['vdagQuery']) == 0:
                    query['clusterQuery'] = {
                        "variable": "vdagURI",
                        "operator": "IN",
                        "value": ids
                    }
                elif 'conditions' in query['vdagQuery']:

                    query['vdagQuery']['conditions'].append({
                        "variable": "vdagURI",
                        "operator": "IN",
                        "value": ids
                    })
                elif 'variable' in query['vdagQuery']:
                    query['vdagQuery'] = {
                        "logicalOperator": "AND",
                        "conditions": [query['vdagQuery'], {
                            "variable": "vdagURI",
                            "operator": "IN",
                            "value": ids
                        }]
                    }


            _, vdags = execute_query("vdag", query['vdagQuery'])
            return vdags
        
        if filter_type == "policy":
            _, policies = execute_query("policy", query['policyQuery'])
            return policies
        
        if filter_type == "policyFunction":
            _, functions = execute_query("policy_function", query['policyFunctionQuery'])
            return functions
        
        if filter_type == "policyGraph":
            _, functions = execute_query("policy_graph", query['policyGraphQuery'])
            return functions

    except Exception as e:
        raise e


class FilterSearch:

    def __init__(self, ir: dict) -> None:
        self.ir = ir

    def execute(self):
        try:

            filter_type = self.ir['matchType']
            filter_query = self.ir['filter']

            results = execute_filter(filter_type, filter_query)
            return results

        except Exception as e:
            raise e


class SimilaritySearch:

    def __init__(self, ir: dict) -> None:

        print('calling remote code executor')
        self.ir = ir
        self.ranking_policy_rule = ir['rankingPolicyRule']

        self.cluster_metrics_api_client = GlobalClusterMetricsClient()
        self.block_metrics_api_client = GlobalBlocksMetricsClient()

        settings = {
            "block_metrics_api": self.block_metrics_api_client,
            "cluster_metrics_api": self.cluster_metrics_api_client
        }

        self.policy_rule = LocalPolicyEvaluator(
            self.ranking_policy_rule['policyRuleURI'], settings=settings, parameters=self.ranking_policy_rule['parameters']
        )

        self.filter = self.ranking_policy_rule['parameters'].get(
            'filterRule', None)

        

    def execute(self):
        try:

            inputs = []

            if self.filter:
                filter_type = self.filter['matchType']
                filter_query = self.filter['filter']
                query_results = execute_filter(filter_type, filter_query)
                inputs = query_results

            result = self.policy_rule.execute_policy_rule(inputs)
            return result

        except Exception as e:
            raise e
