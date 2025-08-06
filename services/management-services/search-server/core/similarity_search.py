import os
import logging

from .webhooks.blocks import BlocksClient
from .policy_sandbox import LocalPolicyEvaluator
from .webhooks.clusters import ClusterClient
from .webhooks.global_metrics import GlobalBlocksMetricsClient, GlobalClusterMetricsClient
from .webhooks.component_registry import ComponentRegistryDB
from .webhooks.vdag import vDAGsClient
from .webhooks.policies import PoliciesQueryClient
from .webhooks.vdag_metrics import vDAGMetricsQuery


def query_translator_old(query):
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
            regex_value = value.replace(".", r"\.").replace("*", ".*")
            return {variable: {"$regex": regex_value}}
        elif operator == "==":
            return {variable: value}
        elif operator == "!=":
            return {variable: {"$ne": value}}
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

        translated = []
        for cond in sub_conditions:
            result = translate_condition(cond)
            # flatten nested logicals of the same type
            if logical_operator in result:
                translated.extend(result[logical_operator])
            else:
                translated.append(result)

        if logical_operator == "AND":
            return {"$and": translated}
        elif logical_operator == "OR":
            return {"$or": translated}
        else:
            raise ValueError(f"Unsupported logical operator: {logical_operator}")

    return translate_condition(query)



def query_translator(query):
    def translate_condition(condition):
        if "logicalOperator" in condition:
            return translate_logical_operator(condition)
        elif "aggOperator" in condition:
            return {"__pipeline__": list(translate_aggregate_condition(condition))}
        else:
            return {"__pipeline__": [{"$match": translate_simple_condition(condition)}]}

    def translate_simple_condition(condition):
        variable = condition["variable"]
        operator = condition["operator"]
        value = condition["value"]

        if operator == "LIKE":
            regex_value = value.replace(".", r"\.").replace("*", ".*")
            return {variable: {"$regex": regex_value}}
        elif operator == "==":
            return {variable: value}
        elif operator == "!=":
            return {variable: {"$ne": value}}
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

        if logical_operator == "AND":
            combined = []
            for sub in sub_conditions:
                translated = translate_condition(sub)
                combined.extend(translated["__pipeline__"])
            return {"__pipeline__": combined}

        elif logical_operator == "OR":
            all_set_stages = []
            or_exprs = []

            for sub in sub_conditions:
                translated = translate_condition(sub)
                stages = translated["__pipeline__"]
                sub_expr = None

                for stage in stages:
                    if "$set" in stage:
                        all_set_stages.append(stage)
                    elif "$match" in stage:
                        match = stage["$match"]
                        if "$expr" in match:
                            sub_expr = match["$expr"]
                        else:
                            sub_expr = {
                                "$and": [{"$eq": [f"${k}", v]} for k, v in match.items()]
                            }

                if sub_expr:
                    or_exprs.append(sub_expr)

            return {
                "__pipeline__": all_set_stages + [
                    {"$match": {"$expr": {"$or": or_exprs}}}
                ]
            }

        else:
            raise ValueError(
                f"Unsupported logical operator: {logical_operator}")

    def translate_aggregate_condition(condition):
        agg = condition["aggOperator"]
        target = condition["target"]
        operator = condition["operator"]
        value = condition["value"]

        computed_field = f"_computed_{agg}_{target.replace('.', '_')}"

        # Handle count separately
        if agg == "count":
            set_stage = {
                "$set": {
                    computed_field: {
                        "$size": {
                            "$ifNull": [f"${target}", []]
                        }
                    }
                }
            }
            match_stage = {
                "$match": {
                    "$expr": {
                        mongo_operator_expr(operator): [f"${computed_field}", value]
                    }
                }
            }
            return [set_stage, match_stage]

        # Generic agg (avg, sum, min, max)
        parts = target.split('.')
        if len(parts) < 2:
            raise ValueError("Aggregate target must have at least two levels")

        array_path = ".".join(parts[:-1])
        field_name = parts[-1]

        if len(parts) >= 3:
            flatten_expr = {
                "$reduce": {
                    "input": f"${'.'.join(parts[:-2])}",
                    "initialValue": [],
                    "in": {"$concatArrays": ["$$value", f"$$this.{parts[-2]}"]}
                }
            }
        else:
            flatten_expr = f"${array_path}"

        map_expr = {
            "$map": {
                "input": flatten_expr,
                "as": "item",
                "in": f"$$item.{field_name}"
            }
        }

        set_stage = {
            "$set": {
                computed_field: {
                    f"${agg}": map_expr
                }
            }
        }

        match_stage = {
            "$match": {
                "$expr": {
                    mongo_operator_expr(operator): [f"${computed_field}", value]
                }
            }
        }

        return [set_stage, match_stage]

    def mongo_operator_expr(op):
        return {
            "==": "$eq",
            "!=": "$ne",
            ">": "$gt",
            ">=": "$gte",
            "<": "$lt",
            "<=": "$lte"
        }.get(op, None)

    result = translate_condition(query)

    if "__pipeline__" in result:
        return result
    else:
        raise ValueError("Invalid query format")


def execute_query(entity_type, query):
    try:

        if entity_type in ["blockMetrics", "clusterMetrics", "vdagMetrics"]:

            db_query = query_translator(query)
            logging.info('db query: {} - {}'.format(entity_type, db_query))

            if "__pipeline__" in db_query:
                pipeline = db_query["__pipeline__"]

                if entity_type == "blockMetrics":
                    return True, GlobalBlocksMetricsClient().aggregate_blocks(pipeline)

                if entity_type == "clusterMetrics":
                    return True, GlobalClusterMetricsClient().aggregate_clusters(pipeline)

                if entity_type == "vdagMetrics":
                    return True, vDAGMetricsQuery().aggregate(pipeline)

                raise Exception(
                    f"Aggregation not allowed for entity type: {entity_type}")
        else:

            db_query = query_translator_old(query)
            logging.info('db query: {} - {}'.format(entity_type, db_query))

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

            if entity_type == "component":
                resp = ComponentRegistryDB().query(db_query)
                return True, resp

            if entity_type == "cluster":
                return ClusterClient().execute_query(db_query)

            if entity_type == "block":
                resp = BlocksClient().query_blocks(db_query)
                return True, resp

        raise Exception("unknown query type")

    except Exception as e:
        raise e


def prepare_metrics_for_blocks(blocks):

    try:

        new_blocks = []

        ids = [block['id'] for block in blocks]
        metrics_data = GlobalBlocksMetricsClient().query_blocks({
            "blockId": {"$in": ids}
        })

        m = {}
        for block in metrics_data:
            m[block['blockId']] = block
        
        for block in blocks:
            block['metrics'] = m.get(block['id'], {})
            new_blocks.append(block)

        return new_blocks
        
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

            return prepare_metrics_for_blocks(blocks)

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
                _, metricsvDAGs = execute_query(
                    'vdagMetrics', query['vdagMetrics'])
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
            _, functions = execute_query(
                "policy_function", query['policyFunctionQuery'])
            return functions

        if filter_type == "policyGraph":
            _, functions = execute_query(
                "policy_graph", query['policyGraphQuery'])
            return functions

    except Exception as e:
        raise e


class FilterSearch:

    def __init__(self, ir: dict) -> None:
        self.ir = ir
        logging.info("received filter IR: {}".format(ir))

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

        logging.info("received search IR: {}".format(ir))
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

            if not inputs or len(inputs) == 0:
                return []

            result = self.policy_rule.execute_policy_rule(inputs)
            return result

        except Exception as e:
            raise e
