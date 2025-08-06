from flask import Flask, request, jsonify
import os
import json

from .drivers import Router

from .k8s_inface import KubernetesInterface
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

@app.route("/cluster-actions/k8s-objects/create", methods=['POST'])
def k8s_create():
    try:

        data = request.get_json()

        k8s_iface = KubernetesInterface()
        k8s_iface.create_resources(data['objects'])

        return jsonify({"success": True, "message": "created objects"}), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/cluster-actions/k8s-objects/remove", methods=['POST'])
def k8s_remove():
    try:

        data = request.get_json()

        k8s_iface = KubernetesInterface()
        k8s_iface.delete_resources(data['objects'])

        return jsonify({"success": True, "message": "created objects"}), 200
        
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
    controller_id = payload.get("vdag_controller_id")
    deployment_name = controller_id
    vdag_uri = payload.get("vdag_uri", "")

    if action == "remove_controller":
        if not deployment_name:
            return jsonify({"success": False, "message": "Missing deployment_name for remove_controller"}), 400

        manager = vDAGInfraManager(deployment_name, "", "")
        manager.remove_controller()

        vdag_controller_db = VDAGControllerClient()
        vdag_controller_db.delete_vdag_controller(deployment_name)

        return jsonify({"success": True, "data": "Controller removed successfully"})

    if action == "list_controllers":
        manager = vDAGInfraManager("", "", "")
        controllers = manager.list_deployments()
        return jsonify({"success": True, "data": controllers})

    config = payload.get('config', {})
    policy_execution_mode = config.get("policy_execution_mode", "local")

    if not deployment_name or not vdag_uri or not policy_execution_mode:
        return jsonify({"success": False, "message": "Missing required parameters"}), 400

    manager = vDAGInfraManager(deployment_name, vdag_uri, policy_execution_mode)

    if action == "create_controller":

        cluster_id = os.getenv("CLUSTER_ID")
        payload['cluster_id'] = cluster_id

        ret, cluster_data = ClusterClient().read_cluster(cluster_id)
        if not ret:
            raise Exception("cluster not found")

        public_url = cluster_data.get('config', {}).get('publicHostname', '')
        if public_url == "":
            raise Exception("failed to determine the public URL for the cluster")

        replicas = config.get("replicas", 1)
        custom_data = config.get("custom_data", None)
        autoscaler_config = config.get('autoscaler', None)

        adhoc_inference_server_url = config.get("inference_server_url")

        if not adhoc_inference_server_url:
            adhoc_inference_server_url = manager.discover_inference_servers()
            if not adhoc_inference_server_url:
                return jsonify({"success": False, "message": "No available inference server found"}), 500

        manager.enable_redis = config.get('enable_redis', False)
        manager.inference_server = adhoc_inference_server_url

        svc_ports = manager.create_controller(replicas, custom_data, autoscaler_config)

        rpc_url = f"{public_url}:{svc_ports.get('grpc')}"
        rest_url = f"http://{public_url}:{svc_ports.get('http')}"
        api_url = f"http://{public_url}:{svc_ports.get('api')}"

        payload['public_url'] = rpc_url

        payload['config'].update({
            "rpc_url": rpc_url,
            "rest_url": rest_url,
            "api_url": api_url
        })
        # Missing: ClusterClient().update_cluster(cluster_id, cluster_data['config'])

        vdag_controller_db = VDAGControllerClient()
        vdag_controller_db.create_vdag_controller(payload)

        return jsonify({"success": True, "data": "Controller created successfully"})

    if action == "scale_controller":
        replicas = payload.get("replicas")
        if replicas is None:
            return jsonify({"success": False, "message": "Missing replicas parameter for scale_controller"}), 400

        manager = vDAGInfraManager(deployment_name, vdag_uri, policy_execution_mode)
        manager.set_scale(replicas)

        vdag_controller_db = VDAGControllerClient()
        vdag_controller_db.update_vdag_controller(deployment_name, {
            "config.replicas": replicas
        })

        return jsonify({"success": True, "data": f"Controller scaled to {replicas} replicas successfully"})

    return jsonify({"success": False, "message": "Invalid action"}), 400



def run_app():
    app.run(host='0.0.0.0', port=4000)
