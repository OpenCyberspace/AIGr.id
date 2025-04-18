from flask import Flask, jsonify
from .scanner import NodesHealth

app = Flask(__name__)


nodes_health = NodesHealth()


@app.route("/healthy_nodes", methods=["GET"])
def get_healthy_nodes():
    try:
        nodes = nodes_health.get_healthy_nodes()
        return jsonify({"success": True, "nodes": nodes})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/nodes_status", methods=["GET"])
def get_nodes_status_api():
    try:
        nodes_status = nodes_health.get_nodes_status()
        return jsonify({"success": True, "nodes_status": nodes_status})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})



def run_server():
    app.run(host="0.0.0.0", port=8500)
