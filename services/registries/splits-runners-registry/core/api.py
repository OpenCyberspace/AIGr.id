from flask import Flask, request, jsonify
import logging
from .crud import SplitRunnerDatabase
from .schema import SplitRunnerObject

from .k8s import K8SplitRunnerAPI

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize the SplitRunner database instance
runner_db = SplitRunnerDatabase()


@app.route('/split-runner', methods=['POST'])
def create_split_runner():
    try:
        payload = request.json
        cluster_k8s_config = payload.pop("cluster_k8s_config", None)
        split_runner_public_host = payload.get("split_runner_public_host", "localhost")

        if cluster_k8s_config is None:
            return jsonify({"success": False, "error": "Missing 'cluster_k8s_config'"}), 400

        # Deploy to cluster and get public URL
        k8_runner = K8SplitRunnerAPI(cluster_k8s_config)
        public_url = k8_runner.deploy_split_runner_and_get_url(public_host=split_runner_public_host)

        # Update payload with the computed public URL
        payload["split_runner_public_url"] = public_url

        runner = SplitRunnerObject.from_dict(payload)
        success, result = runner_db.insert(runner)

        if success:
            return jsonify({"success": True, "data": {"message": "SplitRunner created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_split_runner: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/split-runner/<string:runner_id>', methods=['GET'])
def get_split_runner(runner_id):
    try:
        success, result = runner_db.get_by_runner_id(runner_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_split_runner: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/split-runner/<string:runner_id>', methods=['PUT'])
def update_split_runner(runner_id):
    try:
        update_data = request.json
        success, result = runner_db.update(runner_id, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "SplitRunner updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_split_runner: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/split-runner/<string:runner_id>', methods=['DELETE'])
def delete_split_runner(runner_id):
    try:
        success, result = runner_db.delete(runner_id)
        if success:
            return jsonify({"success": True, "data": {"message": "SplitRunner deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_split_runner: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/split-runners', methods=['POST'])
def query_split_runners():
    try:
        query_filter = request.json
        success, results = runner_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_split_runners: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    app.run(host='0.0.0.0', port=8001)
