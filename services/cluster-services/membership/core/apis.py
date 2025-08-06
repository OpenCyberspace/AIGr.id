from flask import Flask, request, jsonify
from .membership import ClusterMembership, ClusterDeMembership  # Update path if needed

app = Flask(__name__)

membership = ClusterMembership()
demembership = ClusterDeMembership()


@app.route("/pre-checks/add-node", methods=["POST"])
def pre_check_add_node():
    try:
        data = request.json
        allowed, updated_node_data = membership.execute_pre_check(data)
        return jsonify({
            "allowed": allowed,
            "node_data": updated_node_data,
            "success": True
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/pre-checks/add-node/mgmt", methods=["POST"])
def mgmt_add_node():
    try:
        data = request.json
        mgmt_action = data["mgmt_action"]
        mgmt_data = data["mgmt_data"]
        result = membership.execute_mgmt_command(mgmt_action, mgmt_data)
        return jsonify({"result": result, "success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/join-node", methods=["POST"])
def join_node_to_cluster():
    try:
        data = request.json
        mode = data.get("mode", "local_network")
        custom_ip = data.get("custom_ip")
        node_data = data["node_data"]

        result = membership.join_node_to_cluster(node_data, mode, custom_ip)
        return jsonify({"result": result, "success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/pre-checks/remove-node", methods=["POST"])
def pre_check_remove_node():
    try:
        data = request.json
        node_id = data["node_id"]
        allowed, updated_node_id = demembership.execute_pre_check(node_id)
        return jsonify({
            "allowed": allowed,
            "node_id": updated_node_id,
            "success": True
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/pre-checks/remove-node/mgmt", methods=["POST"])
def mgmt_remove_node():
    try:
        data = request.json
        mgmt_action = data["mgmt_action"]
        mgmt_data = data["mgmt_data"]
        result = demembership.execute_mgmt_command(mgmt_action, mgmt_data)
        return jsonify({"result": result, "success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/remove-node", methods=["POST"])
def remove_node_from_cluster():
    try:
        data = request.json
        node_id = data["node_id"]
        

        result = demembership.remove_node_from_cluster(node_id)
        return jsonify({"result": result, "success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
