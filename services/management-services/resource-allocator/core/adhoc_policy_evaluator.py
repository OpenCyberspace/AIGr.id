import threading
from .policy_sandbox import LocalPolicyEvaluator
from .global_metrics import GlobalClusterMetricsClient
from .cluster_db import ClusterClient
from .search import SearchClient

from flask import Flask, request, jsonify


class AdhocResourceAllocator:

    def __init__(self, policy_rule_uri: str, parameters: dict, settings: dict) -> None:
        self.cluster_client = ClusterClient()
        self.metrics_client = GlobalClusterMetricsClient()

        self.search_client = SearchClient()

        settings = settings if settings else {}
        settings.update({
            'cluster_client': self.cluster_client,
            'cluster_metrics_client': self.metrics_client
        })

        self.policy_evaluator = LocalPolicyEvaluator(
            policy_rule_uri, parameters, settings
        )

    def _execute_search(self, input_data):
        if 'filter' in input_data:
            results = self.search_client.filter_data(input_data)
            ids = [data['id'] for data in results]
            return ids

        if 'search' in input_data:
            results = self.search_client.similarity_search(input_data)
            ids = [data['id'] for data in results]
            return ids

    def execute(self, input_data):
        try:

            clusters = input_data.get('clusters', None)

            if not clusters:
                # execute filter or similarity search to get the clusters
                clusters = self._execute_search(input_data)

            global_metrics = GlobalClusterMetricsClient()
            cluster_db = ClusterClient()

            cluster_metrics = global_metrics.query_clusters({
                "clusterId": {"$in": clusters}
            })

            cluster_data = cluster_db.execute_query({
                "id": {"$in": clusters}
            })

            metrics_map = {}
            for entry in cluster_metrics:
                metrics_map[entry['clusterId']] = entry

            # create a map of metrics and cluster data:
            clusters_map = {}

            for cluster in cluster_data:

                clusters_map[cluster['id']] = {
                    "data": cluster,
                    "metrics": metrics_map.get(cluster['id'])
                }

            input_data = input_data['inputs']

            return self.policy_evaluator.execute_policy_rule({
                "cluster_data": clusters_map,
                "inputs": input_data
            })

        except Exception as e:
            raise e


app = Flask(__name__)


def allocate_resources_ws(payload):
    try:
        input_data = payload

        # Validate required fields
        if not input_data or 'policy_rule_uri' not in input_data:
            return {"success": False, "message": "Missing required fields: policy_rule_uri"}

        policy_rule_uri = input_data['policy_rule_uri']
        clusters = input_data.get('clusters', None)
        inputs = input_data['inputs']
        filter = input_data.get('filter', None)
        search = input_data.get('search', None)

        parameters = input_data.get('parameters', {})
        settings = input_data.get('settings', {})

        allocator = AdhocResourceAllocator(policy_rule_uri, parameters, settings)

        result = allocator.execute({"clusters": clusters, "inputs": inputs, "filter": filter, "search": search})

        return {"success": True, "data": result}

    except Exception as e:
        error_message = str(e)
        return {"success": False, "message": error_message}


@app.route('/allocate', methods=['POST'])
def allocate_resources():
    try:
        input_data = request.get_json()

        # Validate required fields
        if not input_data or 'policy_rule_uri' not in input_data:
            return jsonify({"success": False, "message": "Missing required fields: policy_rule_uri"}), 400

        policy_rule_uri = input_data['policy_rule_uri']
        clusters = input_data.get('clusters', None)
        inputs = input_data['inputs']
        filter = input_data.get('filter', None)
        search = input_data.get('search', None)

        parameters = input_data.get('parameters', {})
        settings = input_data.get('settings', {})

        allocator = AdhocResourceAllocator(policy_rule_uri, parameters, settings)

        result = allocator.execute({"clusters": clusters, "inputs": inputs, "filter": filter, "search": search})

        return jsonify({"success": True, "data": result})

    except Exception as e:
        error_message = str(e)
        return jsonify({"success": False, "message": error_message}), 500


def start_server_in_thread(host='0.0.0.0', port=7777):
    server_thread = threading.Thread(target=lambda: app.run(
        host=host, port=port, debug=False, use_reloader=False))
    server_thread.daemon = True
    server_thread.start()
    print(f"Server started in a background thread on {host}:{port}")
