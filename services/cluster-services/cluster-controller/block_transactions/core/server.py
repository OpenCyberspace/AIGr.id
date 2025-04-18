from flask import Flask, jsonify, request
from .blocks import ClusteredBlockClient, BlockUpdater
from .clusters import CurrentClusterClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)


@app.route('/blocks/<block_id>', methods=['GET'])
def get_block_by_id(block_id):
    try:
        client = ClusteredBlockClient()
        result = client.get_block_by_id(block_id)
        if 'error' in result:
            return jsonify({"success": False, "error": result['error']}), 500
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f'Unhandled exception in get_block_by_id: {e}')
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/blocks', methods=['GET'])
def get_all_blocks_in_cluster():
    try:
        client = ClusteredBlockClient()
        result = client.get_all_blocks_in_cluster()
        if 'error' in result:
            return jsonify({"success": False, "error": result['error']}), 500
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f'Unhandled exception in get_all_blocks_in_cluster: {e}')
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/blocks/query', methods=['POST'])
def query_blocks_in_cluster():
    try:
        client = ClusteredBlockClient()

        query = request.json
        result = client.query_blocks_in_cluster(query)
        if 'error' in result:
            return jsonify({"success": False, "error": result['error']}), 500
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f'Unhandled exception in query_blocks_in_cluster: {e}')
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/cluster/get', methods=['GET'])
def read_cluster_from_env():
    try:
        result = CurrentClusterClient().read_cluster_from_env()
        if result is None:
            return jsonify({"success": False, "error": "Cluster not found or environment variable 'CLUSTER_ID' not set"}), 500
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f"Error reading cluster from env: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/cluster/query', methods=['POST'])
def query_cluster():
    try:
        base_query = request.json.get('query', {})
        result = CurrentClusterClient().query(base_query)
        if result is None:
            return jsonify({"success": False, "error": "Query error or environment variable 'CLUSTER_ID' not set"}), 500
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/cluster/update/nodes', methods=['POST'])
def add_node():
    try:
        new_node = request.json
        result = CurrentClusterClient().add_node(new_node)
        if result is None:
            return jsonify({"success": False, "error": "Error adding node or environment variable 'CLUSTER_ID' not set"}), 500
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f"Error adding node: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/cluster/update/config', methods=['POST'])
def update_config():
    try:
        new_config = request.json
        result = CurrentClusterClient().update_config(new_config)
        if result is None:
            return jsonify({"success": False, "error": "Error updating config or environment variable 'CLUSTER_ID' not set"}), 500
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/block/update/<block_id>/metadata', methods=['PUT'])
def update_block_metadata(block_id):
    try:
        metadata = request.json
        updated_metadata = BlockUpdater().update_block_metadata(block_id, metadata)
        response = {"success": True, "data": updated_metadata}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block type
@app.route('/block/update/<block_id>/type', methods=['PUT'])
def update_block_type(block_id):
    try:
        block_type = request.json['blockType']
        updated_block_type = BlockUpdater().update_block_type(block_id, block_type)
        response = {"success": True, "data": updated_block_type}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

@app.route("/block/update/<block_id>", methods=["PUT"])
def update_block_type(block_id):
    try:
        update_data = request.json
        updated_block_data = BlockUpdater().update_block(block_id, update_data)
        response = {"success": True, "data": updated_block_data}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block policies
@app.route('/block/update/<block_id>/policies', methods=['PUT'])
def update_block_policies(block_id):
    try:
        policies = request.json['policies']
        updated_policies = BlockUpdater().update_block_policies(block_id, policies)
        response = {"success": True, "data": updated_policies}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block cluster
@app.route('/block/update/<block_id>/cluster', methods=['PUT'])
def update_block_cluster(block_id):
    try:
        cluster_data = request.json['cluster']
        updated_cluster = BlockUpdater().update_block_cluster(block_id, cluster_data)
        response = {"success": True, "data": updated_cluster}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block init data
@app.route('/block/update/<block_id>/init_data', methods=['PUT'])
def update_block_init_data(block_id):
    try:
        init_data = request.json['blockInitData']
        updated_init_data = BlockUpdater().update_block_init_data(block_id, init_data)
        response = {"success": True, "data": updated_init_data}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block custom metrics
@app.route('/block/update/<block_id>/custom_metrics', methods=['PUT'])
def update_block_custom_metrics(block_id):
    try:
        custom_metrics = request.json['customMetrics']
        updated_custom_metrics = BlockUpdater().update_block_custom_metrics(block_id, custom_metrics)
        response = {"success": True, "data": updated_custom_metrics}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block init settings
@app.route('/block/update/<block_id>/init_settings', methods=['PUT'])
def update_block_init_settings(block_id):
    try:
        init_settings = request.json['initSettings']
        updated_init_settings = BlockUpdater().update_block_init_settings(block_id, init_settings)
        response = {"success": True, "data": updated_init_settings}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block init parameters
@app.route('/block/update/<block_id>/init_parameters', methods=['PUT'])
def update_block_init_parameters(block_id):
    try:
        init_parameters = request.json['initParameters']
        updated_init_parameters = BlockUpdater().update_block_init_parameters(block_id, init_parameters)
        response = {"success": True, "data": updated_init_parameters}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block parameters
@app.route('/block/update/<block_id>/parameters', methods=['PUT'])
def update_block_parameters(block_id):
    try:
        parameters = request.json['parameters']
        updated_parameters = BlockUpdater().update_block_parameters(block_id, parameters)
        response = {"success": True, "data": updated_parameters}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block min instances
@app.route('/block/update/<block_id>/min_instances', methods=['PUT'])
def update_block_min_instances(block_id):
    try:
        min_instances = request.json['minInstances']
        updated_min_instances = BlockUpdater().update_block_min_instances(block_id, min_instances)
        response = {"success": True, "data": updated_min_instances}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block max instances
@app.route('/block/update/<block_id>/max_instances', methods=['PUT'])
def update_block_max_instances(block_id):
    try:
        max_instances = request.json['maxInstances']
        updated_max_instances = BlockUpdater().update_block_max_instances(block_id, max_instances)
        response = {"success": True, "data": updated_max_instances}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block adhoc enabled
@app.route('/block/update/<block_id>/adhoc_enabled', methods=['PUT'])
def update_block_adhoc_enabled(block_id):
    try:
        adhoc_enabled = request.json['adhocEnabled']
        updated_adhoc_enabled = BlockUpdater().update_block_adhoc_enabled(block_id, adhoc_enabled)
        response = {"success": True, "data": updated_adhoc_enabled}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block input protocols
@app.route('/block/update/<block_id>/input_protocols', methods=['PUT'])
def update_block_input_protocols(block_id):
    try:
        input_protocols = request.json['inputProtocols']
        updated_input_protocols = BlockUpdater().update_block_input_protocols(block_id, input_protocols)
        response = {"success": True, "data": updated_input_protocols}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

# Update block output protocols
@app.route('/block/update/<block_id>/output_protocols', methods=['PUT'])
def update_block_output_protocols(block_id):
    try:
        output_protocols = request.json['outputProtocols']
        updated_output_protocols = BlockUpdater().update_block_output_protocols(block_id, output_protocols)
        response = {"success": True, "data": updated_output_protocols}
        return jsonify(response), 200
    except Exception as e:
        response = {"success": False, "error": str(e)}
        return jsonify(response), 500

def run_server():
    app.run('0.0.0.0', port=7500)
