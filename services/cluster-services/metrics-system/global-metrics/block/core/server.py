from flask import Flask, request, jsonify
from .db import BlockMetrics, BlockMetricsListener
import logging
import time

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


@app.route('/block/aggregate', methods=['POST'])
def aggregate():
    try:
        block_metrics = BlockMetrics()
        query_filter = request.get_json()
        success, result = block_metrics.aggregate(query_filter)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in query_blocks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/block/health/<block_id>", methods=["GET"])
def get_health_by_block(block_id):
    try:
        block_metrics = BlockMetrics()
        success, block_data_list = block_metrics.query({"blockId": block_id})
        if not success:
            return jsonify({"success": False, "error": block_data_list}), 400

        if not isinstance(block_data_list, list) or len(block_data_list) == 0:
            return jsonify({"success": False, "error": "No block data found"}), 404

        block_data = block_data_list[0]  # Assuming one result per blockId
        instances = block_data.get("instances", [])
        current_time = time.time()
        instance_health = []

        for instance in instances:
            instance_id = instance.get("instanceId", "unknown")

            if instance_id == "executor":
                instance_health.append({
                    "instanceId": instance_id,
                    "healthy": True,
                    "reason": "executor instance"
                })
                continue

            timestamp = instance.get("timestamp")
            if timestamp is None:
                instance_health.append({
                    "instanceId": instance_id,
                    "healthy": False,
                    "reason": "missing timestamp"
                })
                continue

            time_diff = current_time - timestamp
            if time_diff > 60:
                instance_health.append({
                    "instanceId": instance_id,
                    "healthy": False,
                    "reason": f"stale metrics (last updated {int(time_diff)}s ago)",
                    "lastMetrics": f"{time_diff}s ago"
                })
            else:
                instance_health.append({
                    "instanceId": instance_id,
                    "healthy": True,
                    "lastMetrics": f"{time_diff}s ago"
                })

        overall_health = all(inst["healthy"] for inst in instance_health)

        return jsonify({
            "success": True,
            "block_id": block_id,
            "healthy": overall_health,
            "instances": instance_health
        })

    except Exception as e:
        logger.error(f"Error in get_health_by_block: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def main():
    block_metrics = BlockMetricsListener()
    block_metrics.start_listener()
    app.run(host='0.0.0.0', port=8889, debug=True)
