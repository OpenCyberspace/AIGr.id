from flask import Flask, request, jsonify
import logging
from .crud import VDAGDatabase
from .schema import vDAGObject, vDAGController

app = Flask(__name__)
logger = logging.getLogger(__name__)

vdag_db = VDAGDatabase()
vdag_controller_db = vDAGController()


@app.route('/vdag', methods=['POST'])
def create_vdag():
    try:
        vdag_data = request.json
        vdag = vDAGObject.from_dict(vdag_data)
        success, result = vdag_db.insert(vdag)
        if success:
            return jsonify({"success": True, "data": {"message": "vDAG created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_vdag: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag/<string:vdagURI>', methods=['GET'])
def get_vdag(vdagURI):
    try:
        success, result = vdag_db.get_by_vdagURI(vdagURI)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_vdag: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag/<string:vdagURI>', methods=['PUT'])
def update_vdag(vdagURI):
    try:
        update_data = request.json
        success, result = vdag_db.update(vdagURI, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "vDAG updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_vdag: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag/<string:vdagURI>', methods=['DELETE'])
def delete_vdag(vdagURI):
    try:
        success, result = vdag_db.delete(vdagURI)
        if success:
            return jsonify({"success": True, "data": {"message": "vDAG deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_vdag: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdags', methods=['POST'])
def query_vdags():
    try:
        query_filter = request.json
        success, results = vdag_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_vdags: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag-controller', methods=['POST'])
def create_vdag_controller():
    try:
        controller_data = request.json
        controller = vDAGController.from_dict(controller_data)

        ret, resp = vdag_db.get_by_vdagURI(controller.vdag_uri)
        if not ret:
            raise Exception("vDAG with given vDAG URI not found")
        
        controller.metadata = resp.metadata
        controller.search_tags = resp.discoveryTags

        success, result = vdag_controller_db.insert(controller)
        if success:
            return jsonify({"success": True, "data": {"message": "vDAG Controller created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_vdag_controller: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag-controller/<string:controller_id>', methods=['GET'])
def get_vdag_controller(controller_id):
    try:
        success, result = vdag_controller_db.get_by_id(controller_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_vdag_controller: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag-controller/<string:controller_id>', methods=['PUT'])
def update_vdag_controller(controller_id):
    try:
        update_data = request.json
        success, result = vdag_controller_db.update(controller_id, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "vDAG Controller updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_vdag_controller: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag-controller/<string:controller_id>', methods=['DELETE'])
def delete_vdag_controller(controller_id):
    try:
        success, result = vdag_controller_db.delete(controller_id)
        if success:
            return jsonify({"success": True, "data": {"message": "vDAG Controller deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_vdag_controller: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag-controllers', methods=['POST'])
def query_vdag_controllers():
    try:
        query_filter = request.json
        success, results = vdag_controller_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_vdag_controllers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag-controllers/by-vdag-uri/<string:vdag_uri>', methods=['GET'])
def list_vdag_controllers_by_vdag_uri(vdag_uri):
    try:
        success, results = vdag_controller_db.list_by_vdag_uri(vdag_uri)
        if success:
            return jsonify({"success": True, "data": [ctrl.to_dict() for ctrl in results]}), 200
        else:
            return jsonify({"success": False, "error": results}), 404
    except Exception as e:
        logger.error(f"Error in list_vdag_controllers_by_vdag_uri: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=10501)
