from flask import Flask, request, jsonify
import logging

from .db import ContainerRegistry 
from .schema import ContainerRegistryDatabase  
from .health import is_healthy, get_health_check_data

logger = logging.getLogger(__name__)
app = Flask(__name__)

container_registry_db = ContainerRegistryDatabase()


@app.route('/container_registry', methods=['POST'])
def create_container_registry():
    try:
        registry_data = request.json
        registry = ContainerRegistry.from_dict(registry_data)

        is_healthy(registry.container_registry_public_url)

        success, result = container_registry_db.insert(registry)

        if success:
            return jsonify({"success": True, "data": {"message": "Container registry created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_container_registry: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/container_registry/<string:registry_id>', methods=['GET'])
def get_container_registry(registry_id):
    try:
        success, result = container_registry_db.get_by_container_registry_id(registry_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_container_registry: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/container_registry/<string:registry_id>', methods=['PUT'])
def update_container_registry(registry_id):
    try:
        update_data = request.json
        success, result = container_registry_db.update(registry_id, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Container registry updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_container_registry: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/container_registry/<string:registry_id>', methods=['DELETE'])
def delete_container_registry(registry_id):
    try:
        success, result = container_registry_db.delete(registry_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Container registry deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_container_registry: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/container_registries', methods=['POST'])
def query_container_registries():
    try:
        query_filter = request.json
        success, results = container_registry_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_container_registries: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/check_container_health/<registry_id>", methods=["GET"])
def check_container_health(registry_id):
    try:
        ret, container_entry = container_registry_db.get_by_container_registry_id(registry_id)
        if not ret:
            raise Exception("Container registry not found")

        response = get_health_check_data(container_entry.container_registry_public_url)
        return jsonify({"success": True, "data": response})

    except Exception as e:
        logger.error(f"Error in check_container_health: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    app.run(host='0.0.0.0', port=8000)