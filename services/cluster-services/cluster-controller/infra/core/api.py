from flask import Flask, request, jsonify
import os
import json

from .drivers import Router

from .cluster_actions import ClusterActions
from .vdag_k8s import vDAGInfraManager
from .vdag_controller import VDAGControllerClient
from .cluster_db import ClusterClient

app = Flask(__name__)


@app.route("/executeAction", methods=["POST"])
def executeAction():
    try:

        message = request.get_json()
        router = Router(message)

        result = router.route()

        if result:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": True, "data": "Action performed"})

    except Exception as e:
        return jsonify({"success": False, "data": str(e)}), 500


POLICIES_ACTION_MAP = os.getenv("CLUSTER_ACTIONS_MAP", None)
cluster_actions_map = json.loads(
    POLICIES_ACTION_MAP) if POLICIES_ACTION_MAP else {}

cluster_actions = ClusterActions(cluster_actions_map)


@app.route("/cluster-actions/add-node", methods=["POST"])
def add_node():
    try:
        node_data = request.get_json()
        if not node_data:
            return jsonify({"success": False, "message": "Invalid node data"}), 400

        response = cluster_actions.add_node_to_cluster(node_data)
        return jsonify(response), (200 if response["success"] else 400)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/cluster-actions/remove-node/<string:node_id>", methods=["DELETE"])
def remove_node(node_id):
    try:
        response = cluster_actions.remove_node_from_cluster(node_id)
        return jsonify(response), (200 if response["success"] else 400)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/cluster-actions/get-cluster", methods=["GET"])
def get_cluster():
    try:
        response = cluster_actions.get_cluster_data()
        return jsonify(response), (200 if response["success"] else 400)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/cluster-actions/update-cluster", methods=["PATCH"])
def update_cluster():
    try:
        update_data = request.get_json()
        if not update_data:
            return jsonify({"success": False, "message": "Invalid update data"}), 400

        response = cluster_actions.update_cluster_data(update_data)
        return jsonify(response), (200 if response["success"] else 400)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/vdag-controller", methods=["POST"])
def vdag_controller():
    data = request.get_json()

    if not data or "action" not in data:
        return jsonify({"success": False, "message": "Missing action in request payload"}), 400

    action = data["action"]
    payload = data.get("payload", {})

    controller_id = payload.get('vdag_controller_id')
    deployment_name = controller_id
    vdag_uri = payload.get("vdag_uri", "")

    if action == "remove_controller":
        if not deployment_name:
            return jsonify({"success": False, "message": "Missing deployment_name for remove_controller"}), 400

        manager = vDAGInfraManager(deployment_name, "", "")
        manager.remove_controller()

        # remove from DB:
        vdag_controller_db = VDAGControllerClient()
        vdag_controller_db.delete_vdag_controller(deployment_name)

        return jsonify({"success": True, "data": "Controller removed successfully"})

    if action == "list_controllers":
        manager = vDAGInfraManager("", "", "")
        controllers = manager.list_deployments()
        return jsonify({"success": True, "data": controllers})

    if not deployment_name or not vdag_uri or not policy_execution_mode:
        return jsonify({"success": False, "message": "Missing required parameters"}), 400

    config = payload.get('config')
    policy_execution_mode = config.get("policy_execution_mode", "local")

    manager = vDAGInfraManager(
        deployment_name, vdag_uri, policy_execution_mode)

    if action == "create_controller":
        replicas = config.get("replicas", 1)
        manager.create_controller(replicas)

        cluster_id = os.getenv("CLUSTER_ID")
        payload['cluster_id'] = cluster_id

        ret, cluster_data = ClusterClient().read_cluster(cluster_id)
        if not ret:
            raise Exception("cluster not found")

        config = cluster_data['config']
        urlMap = config['urlMap']

        payload['public_url'] = f"{urlMap['publicGateway']}/{deployment_name}"

        vdag_controller_db = VDAGControllerClient()
        vdag_controller_db.create_vdag_controller(payload)

        return jsonify({"success": True, "data": "Controller created successfully"})

    if action == "scale_controller":
        replicas = payload.get("replicas")
        if replicas is None:
            return jsonify({"success": False, "message": "Missing replicas parameter for scale_controller"}), 400

        manager.set_scale(replicas)
        vdag_controller_db = VDAGControllerClient()
        vdag_controller_db.update_vdag_controller(deployment_name, {
            "config.replicas": replicas
        })

        return jsonify({"success": True, "data": f"Controller scaled to {replicas} replicas successfully"})

    return jsonify({"success": False, "message": "Invalid action"}), 400


def run_app():
    app.run(host='0.0.0.0', port=4000)
