import requests
from .policy_sandbox import LocalPolicyEvaluator
from .clusters import ClusterClient
from .global_metrics import GlobalClusterMetricsClient
import os

class SearchClient:
    def __init__(self):
        self.base_url = os.getenv("SEARCH_SERVER_API_URL", "http://localhost:12000")

    def filter_data(self, input_data):
        try:
            response = requests.post(
                f"{self.base_url}/api/filter-data", json=input_data)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("success"):
                return response_data["data"]
            else:
                raise Exception(response_data.get(
                    "message", "Unknown error occurred"))

        except Exception as e:
            raise Exception(f"Error in filter_data: {str(e)}")

    def similarity_search(self, input_data):
        try:
            response = requests.post(
                f"{self.base_url}/api/similarity-search", json=input_data)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("success"):
                return response_data["data"]
            else:
                raise Exception(response_data.get("message", "Unknown error occurred"))

        except Exception as e:
            raise Exception(f"Error in similarity_search: {str(e)}")

def execute_cluster_selection(cluster_query):

    if 'filter' in cluster_query:
        search_server = SearchClient()
        return search_server.filter_data(cluster_query['filter'])
    else:
        ids = cluster_query.get('ids')
        if not ids:
            raise Exception("no clusters provided for filter criteria")
        
        selected_clusters = ClusterClient().execute_query({
            "id": {"$in": ids}
        })

        return selected_clusters

def prepare_metrics_function():
    cluster_metrics = GlobalClusterMetricsClient()
    return cluster_metrics.get_cluster, cluster_metrics.query_clusters

def execute_splitting_policy(policy_data):
    try:

        policy = policy_data.get('policy')
        clusters_selector = policy_data.get('clustersSelector')
        parameters = policy.get('parameters')
        input_data = policy_data.get('inputs')
        policy_rule_uri = policy.get('policyRuleURI')

        selected_clusters = execute_cluster_selection(clusters_selector)
        metrics_function, metrics_query_function = prepare_metrics_function()

        settings = {
            "get_cluster_metrics": metrics_function,
            "query_cluster_metrics": metrics_query_function
        }

        policy_evaluator = LocalPolicyEvaluator(policy_rule_uri, parameters, settings)
        ranking_data = policy_evaluator.execute_policy_rule({
            "selected_clusters": selected_clusters,
            "extra_input": input_data
        })

        return  ranking_data
        
    except Exception as e:
        raise e

