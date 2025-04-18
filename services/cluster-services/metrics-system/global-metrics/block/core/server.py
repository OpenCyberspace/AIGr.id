from flask import Flask, request, jsonify
from .db import BlockMetrics, BlockMetricsListener
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.route('/block', methods=['POST'])
def create_block():
    try:
        block_metrics = BlockMetrics()
        document = request.json
        success, result = block_metrics.insert(document)
        if success:
            return jsonify({"success": True, "data": {"message": "Block created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_block: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/block/<block_id>', methods=['PUT'])
def update_block(block_id):
    try:
        block_metrics = BlockMetrics()
        update_fields = request.json
        success, result = block_metrics.update(block_id, update_fields)
        if success:
            return jsonify({"success": True, "data": {"message": "Block updated", "modified_count": result}}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in update_block: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/block/<block_id>', methods=['DELETE'])
def delete_block(block_id):
    try:
        block_metrics = BlockMetrics()
        success, result = block_metrics.delete(block_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Block deleted", "deleted_count": result}}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in delete_block: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/block/<block_id>', methods=['GET'])
def get_block(block_id):
    try:
        block_metrics = BlockMetrics()
        success, result = block_metrics.query({"blockId": block_id})
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in get_block: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/block/query', methods=['POST'])
def query_blocks():
    try:
        block_metrics = BlockMetrics()
        query_filter = request.get_json()
        success, result = block_metrics.query(query_filter)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in query_blocks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def main():
    block_metrics = BlockMetricsListener()
    block_metrics.start_listener()
    app.run(host='0.0.0.0', port=8889, debug=True)
