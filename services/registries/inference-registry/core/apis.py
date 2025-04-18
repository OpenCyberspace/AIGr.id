from flask import Flask, request, jsonify
import logging
from .schema import InferenceServer
from .db import InferenceServerDatabase

app = Flask(__name__)
logger = logging.getLogger(__name__)

inference_server_db = InferenceServerDatabase()


@app.route('/inference_server', methods=['POST'])
def create_inference_server():
    try:
        server_data = request.json
        server = InferenceServer.from_dict(server_data)

        success, result = inference_server_db.insert(server)

        if success:
            return jsonify({"success": True, "data": {"message": "Inference server created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_inference_server: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/inference_server/<string:server_id>', methods=['GET'])
def get_inference_server(server_id):
    try:
        success, result = inference_server_db.get_by_inference_server_id(
            server_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_inference_server: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/inference_server/<string:server_id>', methods=['PUT'])
def update_inference_server(server_id):
    try:
        update_data = request.json
        success, result = inference_server_db.update(server_id, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Inference server updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_inference_server: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/inference_server/<string:server_id>', methods=['DELETE'])
def delete_inference_server(server_id):
    try:
        success, result = inference_server_db.delete(server_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Inference server deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_inference_server: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/inference_servers', methods=['POST'])
def query_inference_servers():
    try:
        query_filter = request.json
        success, results = inference_server_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_inference_servers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    app.run(host='0.0.0.0', port=6000)
