from flask import Flask, request, jsonify
import logging
from .crud import ModelLayerDatabase
from .schema import ModelLayerObject

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize the ModelLayer database instance
layer_db = ModelLayerDatabase()


@app.route('/model-layer', methods=['POST'])
def create_model_layer():
    try:
        payload = request.json
        layer = ModelLayerObject.from_dict(payload)
        success, result = layer_db.insert(layer)

        if success:
            return jsonify({"success": True, "data": {"message": "ModelLayer created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_model_layer: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/model-layer/<string:layer_hash>', methods=['GET'])
def get_model_layer(layer_hash):
    try:
        success, result = layer_db.get_by_layer_hash(layer_hash)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_model_layer: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/model-layer/<string:layer_hash>', methods=['PUT'])
def update_model_layer(layer_hash):
    try:
        update_data = request.json
        success, result = layer_db.update(layer_hash, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "ModelLayer updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_model_layer: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/model-layer/<string:layer_hash>', methods=['DELETE'])
def delete_model_layer(layer_hash):
    try:
        success, result = layer_db.delete(layer_hash)
        if success:
            return jsonify({"success": True, "data": {"message": "ModelLayer deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_model_layer: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/model-layers', methods=['POST'])
def query_model_layers():
    try:
        query_filter = request.json
        success, results = layer_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_model_layers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    app.run(host='0.0.0.0', port=8002)  # Use different port if needed
