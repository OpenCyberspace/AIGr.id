from flask import Flask, request, jsonify
import logging
from .crud import SpecStoreDatabase
from .schema import SpecStoreObject

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize the SpecStore database instance
spec_db = SpecStoreDatabase()


@app.route('/spec', methods=['POST'])
def create_spec():
    try:
        spec_data = request.json
        spec = SpecStoreObject.from_dict(spec_data)
        success, result = spec_db.insert(spec)
        if success:
            return jsonify({"success": True, "data": {"message": "Spec created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_spec: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/spec/<string:specUri>', methods=['GET'])
def get_spec(specUri):
    try:
        success, result = spec_db.get_by_specUri(specUri)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_spec: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/spec/<string:specUri>', methods=['PUT'])
def update_spec(specUri):
    try:
        update_data = request.json
        success, result = spec_db.update(specUri, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Spec updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_spec: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/spec/<string:specUri>', methods=['DELETE'])
def delete_spec(specUri):
    try:
        success, result = spec_db.delete(specUri)
        if success:
            return jsonify({"success": True, "data": {"message": "Spec deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_spec: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/specs', methods=['POST'])
def query_specs():
    try:
        query_filter = request.json
        success, results = spec_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_specs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    app.run(host='0.0.0.0', port=8000)
