from kubernetes import client, config
from flask import Flask, jsonify, request
from core.k8s import scan_pods_in_namespace, query_metrics
from core.k8s import start_update_notifier

import os

app = Flask(__name__)

start_update_notifier()

@app.route('/getInstances', methods=['GET'])
def get_instances():
    namespace = "blocks"
    block_id = os.getenv("BLOCK_ID")
    if not namespace or not block_id:
        return jsonify({"success": False, "data": "namespace and blockID query parameters are required"}), 400

    try:
        pods = scan_pods_in_namespace(namespace, block_id)
        pods_data = [pod.to_dict() for pod in pods]
        return jsonify({"success": True, "data": pods_data})
    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/getInstancesCount', methods=['GET'])
def get_instances_count():
    namespace = "blocks"
    block_id = os.getenv("BLOCK_ID")
    if not namespace or not block_id:
        return jsonify({"success": False, "data": "namespace and blockID query parameters are required"}), 400

    try:
        pods = scan_pods_in_namespace(namespace, block_id)
        return jsonify({"success": True, "data": len(pods)})
    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/queryMetrics', methods=['POST'])
def query_metrics_api():
    data = request.get_json()
    namespace = data.get('namespace')
    block_id = data.get('blockID')
    prometheus_url = os.getenv("CLUSTER_PROMETHEUS_URL")

    if not namespace or not block_id or not prometheus_url:
        return jsonify({"success": False, "data": "namespace, blockID, and prometheus_url are required in the payload"}), 400

    try:
        results = query_metrics(namespace, block_id, prometheus_url)
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
