from flask import Flask, jsonify, request
import logging
import os
import json
import requests

from .cluster_metrics import get_cluster_metrics_connection
from .cluster_db import ClusterClient
from .cluster_controller import get_cluster_controller_connection, get_cluster_controller_connection_url
from .block_scheduling import BlockCreator, BlocksTaskHandler
from .infra import K8sInfraCreateTaskHandler
from .mgmt import BlockManagementService

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_cluster_policy_map():
    data = os.getenv("CLUSTER_CONTROLLER_GATEWAY_POLICY_MAP", "{}")
    return json.loads(data)


@app.route('/cluster-metrics/node/<cluster_id>/<node_id>', methods=['GET'])
def get_node(cluster_id, node_id):
    try:

        client = get_cluster_metrics_connection(cluster_id)

        success, result = client.get_node(node_id)
        if success:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_node endpoint: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/cluster-metrics/<cluster_id>/node/query', methods=['POST'])
def query_node(cluster_id):
    try:

        client = get_cluster_metrics_connection(cluster_id)
        query_params = request.args.to_dict()
        success, result = client.query_node(query_params)
        if success:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Unexpected error in query_node endpoint: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/cluster-metrics/<cluster_id>', methods=['GET'])
def get_cluster_metrics(cluster_id):
    try:
        client = get_cluster_metrics_connection(cluster_id)
        success, result = client.get_cluster_metrics()
        if success:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_cluster_metrics endpoint: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/clusters/create', methods=['POST'])
def create_cluster():
    try:
        cluster_data = request.get_json()
        success, result = ClusterClient().create_cluster(cluster_data)
        if success:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Unexpected error in create_cluster endpoint: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/clusters/read/<cluster_id>', methods=['GET'])
def read_cluster(cluster_id):
    try:
        success, result = ClusterClient().read_cluster(cluster_id)
        if success:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Unexpected error in read_cluster endpoint: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/clusters/update/<cluster_id>', methods=['PUT'])
def update_cluster(cluster_id):
    try:
        update_data = request.get_json()
        success, result = ClusterClient().update_cluster(cluster_id, {
            "$set": update_data
        })

        if success:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Unexpected error in update_cluster endpoint: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/clusters/delete/<cluster_id>', methods=['DELETE'])
def delete_cluster(cluster_id):
    try:
        success, result = ClusterClient().delete_cluster(cluster_id)
        if success:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Unexpected error in delete_cluster endpoint: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/clusters/query', methods=['POST'])
def execute_query():
    try:
        query = request.get_json().get('query')
        success, result = ClusterClient().execute_query(query)
        if success:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Unexpected error in execute_query endpoint: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/controller/removeBlock/<cluster_id>', methods=['POST'])
def remove_block(cluster_id):
    try:
        executor = get_cluster_controller_connection(cluster_id)
        payload = request.get_json()
        result = executor.remove_block(payload)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/controller/createBlock/<cluster_id>', methods=['POST'])
def create_block(cluster_id):
    try:
        executor = get_cluster_controller_connection(cluster_id)
        payload = request.get_json()
        result = executor.create_block(payload)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/controller/block-scaling/<cluster_id>', methods=['POST'])
def scale_instance(cluster_id):
    try:
        executor = get_cluster_controller_connection(cluster_id)
        payload = request.get_json()
        result = executor.scale_instance(payload)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/controller/removeInstance/<cluster_id>', methods=['POST'])
def remove_instance(cluster_id):
    try:
        executor = get_cluster_controller_connection(cluster_id)
        payload = request.get_json()
        result = executor.remove_instance(payload)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/controller/resourceAllocation/<cluster_id>', methods=['POST'])
def resource_allocation(cluster_id):
    try:
        executor = get_cluster_controller_connection(cluster_id)
        payload = request.get_json()
        result = executor.resource_allocation(payload)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


@app.route("/blockActions/selectClusters", methods=["POST"])
def select_clusters():
    try:
        data = request.json
        block_creator = BlockCreator(data, mode="select_clusters")
        result = block_creator.execute()

        print(f'sending result: {result}')
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in select_clusters endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/blockActions/allocate", methods=["POST"])
def allocate():
    try:
        data = request.json

        task_handler = BlocksTaskHandler(data)
        task_id = task_handler.execute_allocation()
        return jsonify({"success": True, "data": {"message": "task scheduled in background", "task_id": task_id}}), 200
    except Exception as e:
        logging.error(f"Error in allocate endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/blockActions/dryRun", methods=["POST"])
def dry_run():
    try:
        data = request.json

        task_handler = BlocksTaskHandler(data)
        task_id = task_handler.execute_dry_run()
        return jsonify({"success": True, "data": {"message": "task scheduled in background", "task_id": task_id}}), 200
    except Exception as e:
        logging.error(f"Error in dry_run endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/create-cluster-infra', methods=['POST'])
def create_cluster_infra_api():
    try:
        data = request.get_json()
        kube_config_data = data.get("kube_config_data")
        cluster_id = data.get("cluster_id")

        if not kube_config_data or not cluster_id:
            return jsonify({"error": "Missing 'kube_config_data' or 'cluster_id'"}), 400

        k8s_infra = K8sInfraCreateTaskHandler(cluster_id, kube_config_data)
        task_id = k8s_infra.create()

        return jsonify({"success": True, "data": {"message": "scheduled in background", "task_id":  task_id}}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/remove-cluster-infra', methods=['POST'])
def remove_cluster_infra_api():
    try:
        data = request.get_json()
        kube_config_data = data.get("kube_config_data")
        cluster_id = data.get("cluster_id")

        k8s_infra = K8sInfraCreateTaskHandler(cluster_id, kube_config_data)
        task_id = k8s_infra.remove()

        return jsonify({"success": True, "data": {"message": "scheduled in background", "task_id":  task_id}}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/nodes/add-node-to-cluster/<cluster_id>', methods=['POST'])
def add_node_to_cluster(cluster_id):
    try:

        node_data = request.get_json()
        cluster_client = ClusterClient()
        result = cluster_client.add_node_to_cluster(cluster_id, node_data)

        return {"success": True, "data": result}

    except Exception as e:
        return {"success": False, "message": result}, 500


@app.route('/nodes/remove-node-from-cluster/<cluster_id>/<node_id>', methods=['GET'])
def add_node_to_cluster(cluster_id, node_id):
    try:
        cluster_client = ClusterClient()
        result = cluster_client.remove_node_from_cluster(cluster_id, node_id)

        return {"success": True, "data": result}

    except Exception as e:
        return {"success": False, "message": result}, 500


@app.route("/vdag-controller/<cluster_id>", methods=["POST"])
def proxy_vdag_controller(cluster_id):
    try:
        data = request.get_json()

        if not data or "action" not in data:
            return jsonify({"success": False, "message": "Missing action in request payload"}), 400

        base_url = get_cluster_controller_connection_url(cluster_id)
        base_url = base_url + '/vdag-controller'
        response = requests.post(base_url, json=data)

        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/initContainer/initCreateStatusUpdate/<cluster_id>", methods=["POST"])
def init_create_status_update(cluster_id):
    try:
        data = request.json
        cluster_connection = get_cluster_controller_connection(cluster_id)
        result = cluster_connection.init_create_status_update(data)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in init_create_status_update endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/initContainer/queryInitContainerData/<cluster_id>", methods=["POST"])
def query_init_container_data(cluster_id):
    try:
        data = request.json
        cluster_connection = get_cluster_controller_connection(cluster_id)
        result = cluster_connection.query_init_container_data(data)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in query_init_container_data endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/blocks/mgmt', methods=['POST'])
def execute_mgmt():
    try:
        # Parse JSON request data
        data = request.get_json()

        block_mgmt_service = BlockManagementService()

        if not data:
            return jsonify({"error": "Invalid JSON input"}), 400

        cluster_id = data.get('cluster_id')
        block_id = data.get("block_id")
        service = data.get("service")
        mgmt_command = data.get("action")
        mgmt_data = data.get("payload", {})

        if not all([block_id, service, mgmt_command]):
            return jsonify({"error": "Missing required fields: block_id, service, mgmt_command"}), 400

        # Execute management command
        result = block_mgmt_service.execute_mgmt_command(block_id, service, mgmt_command, mgmt_data)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pre-check-policies/update", method=["POST"])
def update_pre_check_policies():
    try:
        pass
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_app():
    app.run(port=5000, debug=True)
