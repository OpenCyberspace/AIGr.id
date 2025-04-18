from flask import Flask, request, jsonify
from .db import AssetRegistryDatabase, AssetRegistry

from .health import is_healthy, get_health_check_data

import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)
asset_registry_db = AssetRegistryDatabase()


@app.route('/asset_registry', methods=['POST'])
def create_asset_registry():
    try:
        registry_data = request.json
        registry = AssetRegistry.from_dict(registry_data)

        is_healthy(registry.asset_registry_public_url)

        success, result = asset_registry_db.insert(registry)

        if success:
            return jsonify({"success": True, "data": {"message": "Asset registry created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_asset_registry: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/asset_registry/<string:registry_id>', methods=['GET'])
def get_asset_registry(registry_id):
    try:
        success, result = asset_registry_db.get_by_registry_id(registry_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_asset_registry: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/asset_registry/<string:registry_id>', methods=['PUT'])
def update_asset_registry(registry_id):
    try:
        update_data = request.json
        success, result = asset_registry_db.update(registry_id, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Asset registry updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_asset_registry: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/asset_registry/<string:registry_id>', methods=['DELETE'])
def delete_asset_registry(registry_id):
    try:
        success, result = asset_registry_db.delete(registry_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Asset registry deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_asset_registry: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/asset_registries', methods=['POST'])
def query_asset_registries():
    try:
        query_filter = request.json
        success, results = asset_registry_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_asset_registries: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/check_health/<asset_db_id>", methods=["GET"])
def check_health(asset_db_id):
    try:

        ret, asset_db_entry = asset_registry_db.get_by_asset_registry_id(asset_db_id)
        if not ret:
            raise Exception("asset DB not found")

        response = get_health_check_data(
            asset_db_entry.asset_registry_public_url)
        return jsonify({"success": True, "data": response})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    app.run(host='0.0.0.0', port=4000)
