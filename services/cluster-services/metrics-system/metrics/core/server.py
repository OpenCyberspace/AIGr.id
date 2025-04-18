from flask import Flask, jsonify, request
import logging
import os

from .db import Cluster, MetricsListener, BlockMetrics
from .db import ClusterMetricsWriterThread

app = Flask(__name__)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CLUSTER_ID = os.getenv("CLUSTER_ID", "cluster-123")


@app.route('/node', methods=['POST'])
def create_node():
    try:
        cluster = Cluster()
        node_metrics = cluster.node_metrics
        document = request.json
        success, result = node_metrics.insert(document)
        if success:
            return jsonify({"success": True, "data": {"message": "Node created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_node: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/node/<node_id>', methods=['PUT'])
def update_node(node_id):
    try:
        cluster = Cluster()
        node_metrics = cluster.node_metrics
        update_fields = request.json
        success, result = node_metrics.update(node_id, update_fields)
        if success:
            return jsonify({"success": True, "data": {"message": "Node updated", "modified_count": result}}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in update_node: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/node/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    try:
        cluster = Cluster()
        node_metrics = cluster.node_metrics
        success, result = node_metrics.delete(node_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Node deleted", "deleted_count": result}}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in delete_node: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/node/<node_id>', methods=['GET'])
def get_node(node_id):
    try:
        cluster = Cluster()
        node_metrics = cluster.node_metrics
        success, result = node_metrics.query({"nodeId": node_id})
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in get_node: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/node/query', methods=['POST'])
def query_node():
    try:
        cluster = Cluster()
        node_metrics = cluster.node_metrics
        query_filter = request.get_json()
        success, result = node_metrics.query(query_filter)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in query_node: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/block/insert', methods=['POST'])
def insert_document():
    try:
        document = request.json
        success, result = BlockMetrics().insert(document)
        if success:
            return jsonify({"success": True, "data": str(result)}), 200
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Error in /insert: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/block/update', methods=['PUT'])
def update_document():
    try:
        node_id = request.json.get("nodeId")
        update_fields = request.json.get("updateFields")
        success, result = BlockMetrics().update(node_id, update_fields)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Error in /update: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/block/delete', methods=['DELETE'])
def delete_document():
    try:
        node_id = request.json.get("nodeId")
        success, result = BlockMetrics().delete(node_id)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Error in /delete: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route("/block/<block_id>", methods=["GET"])
def get_by_block_id(block_id: str):
    try:

        success, result = BlockMetrics().get_all_metrics(block_id)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Error in /block/<block_id>: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/block/query', methods=['POST'])
def query_documents():
    try:
        query_filter = request.json
        success, result = BlockMetrics().query(query_filter)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "data": result}), 500
    except Exception as e:
        logger.error(f"Error in /query: {e}")
        return jsonify({"success": False, "data": str(e)}), 500


@app.route('/cluster', methods=['GET'])
def get_cluster_metrics():
    try:
        cluster = Cluster()
        success, result = cluster.get_all_metrics(CLUSTER_ID)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in get_cluster_metrics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run():
    while True:
        listener = MetricsListener()
        listener.start_listener()

        writer = ClusterMetricsWriterThread(30)
        writer.start()

        logger.info("started metrics listener in background")

        app.run("0.0.0.0", port=5000)
