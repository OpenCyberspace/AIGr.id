from flask import Flask, request, jsonify
import logging

from .db import NetworkDatabase
from .schema import NetworkObject

app = Flask(__name__)
logger = logging.getLogger(__name__)
network_db = NetworkDatabase()

@app.route('/network', methods=['POST'])
def create_network():
    try:
        network_data = request.json
        network = NetworkObject.from_dict(network_data)
        success, result = network_db.insert(network)
        if success:
            return jsonify({"success": True, "data": {"message": "Network created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_network: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/network/<string:network_id>', methods=['GET'])
def get_network(network_id):
    try:
        success, result = network_db.get_by_network_id(network_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_network: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/network/<string:network_id>', methods=['PUT'])
def update_network(network_id):
    try:
        update_data = request.json
        success, result = network_db.update(network_id, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Network updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_network: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/network/<string:network_id>', methods=['DELETE'])
def delete_network(network_id):
    try:
        success, result = network_db.delete(network_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Network deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_network: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/networks', methods=['POST'])
def query_networks():
    try:
        query_filter = request.json
        success, results = network_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_networks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def run_server():
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=5000)
