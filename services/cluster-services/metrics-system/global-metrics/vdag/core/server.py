from flask import Flask, request, jsonify
from .db import VDAGMetrics
from .db import VDAGMetricsListener
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.route('/vdag', methods=['POST'])
def create_vdag():
    try:
        vdag_metrics = VDAGMetrics()
        document = request.json
        success, result = vdag_metrics.insert(document)
        if success:
            return jsonify({"success": True, "data": "VDAG created"}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_vdag: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag/<vdag_id>', methods=['PUT'])
def update_vdag(vdag_id):
    try:
        vdag_metrics = VDAGMetrics()
        update_fields = request.json
        success, result = vdag_metrics.update(vdag_id, update_fields)
        if success:
            return jsonify({"success": True, "data": {"message": "VDAG updated", "modified_count": result}}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in update_vdag: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/vdag/<vdag_id>', methods=['DELETE'])
def delete_vdag(vdag_id):
    try:
        vdag_metrics = VDAGMetrics()
        success, result = vdag_metrics.delete(vdag_id)
        if success:
            return jsonify({"success": True, "data": {"message": "VDAG deleted", "deleted_count": result}}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in delete_vdag: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag/<vdag_id>', methods=['GET'])
def get_vdag(vdag_id):
    try:
        vdag_metrics = VDAGMetrics()
        success, result = vdag_metrics.query({"vdagControllerId": vdag_id})
        if success:
            if len(result) == 0:
                return jsonify({"success": False, "message": "VDAG not found"}), 400

            result = result[0]
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in get_vdag: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/vdag/query', methods=['POST'])
def query_vdags():
    try:
        vdag_metrics = VDAGMetrics()
        query_filter = request.json
        success, result = vdag_metrics.query(query_filter)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in query_vdags: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/block/aggregate', methods=['POST'])
def query_blocks():
    try:
        vdag_metrics = VDAGMetrics()
        query_filter = request.get_json()
        success, result = vdag_metrics.aggregate(query_filter)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in query_blocks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def main():
    vdag_listener = VDAGMetricsListener()
    vdag_listener.start_listener()

    app.run(host='0.0.0.0', port=8890)
