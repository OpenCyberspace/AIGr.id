from flask import Flask, jsonify, request
from .monitor import ClusterStabilityChecker
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize once at startup
stability_checker = ClusterStabilityChecker()


@app.route("/check_stability", methods=["GET"])
def check_stability():
    try:
        logger.info("Received request to check cluster stability")
        nodes_status = stability_checker.nodes_client.get_nodes_status()
        stability_checker.executor.evaluate(nodes_status)
        return jsonify({
            "success": True,
            "message": "Cluster stability check passed"
        }), 200
    except Exception as e:
        logger.exception("Cluster stability check failed")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route("/mgmt", methods=["POST"])
def mgmt():
    try:
        data = request.json
        mgmt_action = data['mgmt_action']
        mgmt_data = data['mgmt_data']

        result = stability_checker.executor.policy.execute_mgmt_command(
            mgmt_action, mgmt_data
        )

        return jsonify({"success": True, "data": result})
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

def run_server():
    stability_checker.start()
    app.run(host="0.0.0.0", port=5000)
