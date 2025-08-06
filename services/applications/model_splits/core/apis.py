from flask import Flask, request, jsonify
from .schema import SplitsDeploymentEntry
from .crud import SplitsDeploymentDB
from .crud import create_splits_deployment, remove_splits_deployment

import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


@app.route("/splits/create", methods=["POST"])
def create_splits():
    try:
        data = request.get_json()
        entry = SplitsDeploymentEntry.from_dict(data)

        create_splits_deployment(entry)
        return jsonify({"success": True, "message": f"Deployment '{entry.deployment_name}' created."}), 200

    except Exception as e:
        logger.error(f"Create API failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/splits/delete/<deployment_name>", methods=["DELETE"])
def delete_splits(deployment_name):
    try:
        remove_splits_deployment(deployment_name)
        return jsonify({"success": True, "message": f"Deployment '{deployment_name}' removed."}), 200

    except Exception as e:
        logger.error(f"Delete API failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/splits/query", methods=["POST"])
def query_splits():
    try:
        query_filter = request.get_json()
        db = SplitsDeploymentDB()
        success, results = db.query(query_filter)
        if success:
            return jsonify({"success": True, "results": results}), 200
        else:
            return jsonify({"success": False, "message": results}), 404

    except Exception as e:
        logger.error(f"Query API failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/splits/get/<deployment_name>", methods=["GET"])
def get_splits_by_name(deployment_name):
    try:
        db = SplitsDeploymentDB()
        success, result = db.get_by_deployment_name(deployment_name)
        if success:
            return jsonify({"success": True, "result": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "message": result}), 404

    except Exception as e:
        logger.error(f"Get API failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


def run_server():
    app.run(debug=True, port=5000)
