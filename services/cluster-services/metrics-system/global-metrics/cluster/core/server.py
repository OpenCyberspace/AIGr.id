from flask import Flask, request, jsonify
from .db import ClusterMetrics
from .db import ClusterMetricsListener
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.route('/cluster', methods=['POST'])
def create_cluster():
    try:
        cluster_metrics = ClusterMetrics()
        document = request.json
        success, result = cluster_metrics.insert(document)
        if success:
            return jsonify({"success": True, "data": "cluster created"}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_cluster: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/cluster/<cluster_id>', methods=['PUT'])
def update_cluster(cluster_id):
    try:
        cluster_metrics = ClusterMetrics()
        update_fields = request.json
        success, result = cluster_metrics.update(cluster_id, update_fields)
        if success:
            return jsonify({"success": True, "data": {"message": "Cluster updated", "modified_count": result}}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in update_cluster: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/cluster/<cluster_id>', methods=['DELETE'])
def delete_cluster(cluster_id):
    try:
        cluster_metrics = ClusterMetrics()
        success, result = cluster_metrics.delete(cluster_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Cluster deleted", "deleted_count": result}}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in delete_cluster: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/cluster/<cluster_id>', methods=['GET'])
def get_cluster(cluster_id):
    try:
        cluster_metrics = ClusterMetrics()
        success, result = cluster_metrics.query({"clusterId": cluster_id})
        if success:
            if len(result) == 0:
                return jsonify({"success": False, "message": "cluster not found"}), 400

            result = result[0]
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in get_cluster: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/cluster/query', methods=['POST'])
def query_clusters():
    try:
        cluster_metrics = ClusterMetrics()
        query_filter = request.json
        success, result = cluster_metrics.query(query_filter)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in query_clusters: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def main():
    cluster_listener = ClusterMetricsListener()
    cluster_listener.start_listener()

    app.run(debug=True, port=8888)
