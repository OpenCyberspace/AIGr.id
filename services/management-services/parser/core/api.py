# app.py

from .IR import (
    block_create_IR,
    cluster_create_IR,
    create_vdag_IR,
    llm_create_IR,
    llm_vdag_manual_create_IR,
    search_IR
)

from .actions import create_cluster, similarity_search, filter_data, execute_block_action, add_node
from .actions import execute_vdag_create, execute_create_llm_vdag, execute_mgmt_command
from .modules.llm_planner import TaskClient, LayerClient

from .webhooks.spec_store import SpecAPIClient

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from .task_db import db, init_db, create_task, get_task, update_task_status, query_tasks

ENABLE_TASK_DB = os.getenv("ENABLE_TASK_DB", "False") == "True"


app = Flask(__name__)
task_client = TaskClient(base_url=os.getenv("LLM_PLANNER_TASK_API"))
layer_client = LayerClient(base_url=os.getenv("LLM_LAYERS_API"))


# Initialize the Task DB with Flask app
if ENABLE_TASK_DB:
    init_db(app)


type_action_dispatcher = {
    "createBlock": execute_block_action,
    "createCluster": create_cluster,
    "createvDAG": execute_vdag_create,
    "parameterUpdate": None,
    "llmCreate": llm_create_IR,
    "llmVDAGCreateManual": llm_vdag_manual_create_IR,
    "search": similarity_search,
    "filter": filter_data,
    "llmVDAGCreate": execute_create_llm_vdag,
    "addNode": add_node,
    "executeMgmtCommand": execute_mgmt_command
}


def format_response(response):
    if "error" in response:
        return jsonify({"success": False, "message": response["error"]}), 400
    return jsonify({"success": True, "data": response})


def ir(spec: dict, action: str):
    if action not in type_action_dispatcher:
        raise ValueError(f"Invalid action: {action}")

    action_function = type_action_dispatcher[action]
    return action_function(spec) if action_function else None


@app.route('/api/<action>', methods=['POST'])
def handle_action(action):
    try:

        json_data = request.get_json()
        if not json_data:
            return jsonify({"error": "Invalid JSON input"}), 400

        # Create a task entry in the DB
        task_id = ""

        if ENABLE_TASK_DB:
            task_id = create_task(payload=json_data, action=action)

        result = ir(json_data, action)
        if result is None:
            return jsonify({"success": False, "message": f"Action {action} is not implemented"}), 400

        # Return response with task_id
        return jsonify({"success": True, "task_id": task_id, "result": result}), 200

    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/with-spec/<action>', methods=['POST'])
def handle_action(action):
    try:

        spec_client = SpecAPIClient()

        spec_uri = request.args.get('specUri', None)
        if not spec_uri:
            return jsonify({"success": False, "error": "specUri not provided"})

        spec_data = spec_client.get_spec(spec_uri)

        json_data = spec_data['specData']

        # Create a task entry in the DB
        task_id = ""

        if ENABLE_TASK_DB:
            task_id = create_task(payload=json_data, action=action)

        result = ir(json_data, action)
        if result is None:
            return jsonify({"success": False, "message": f"Action {action} is not implemented"}), 400

        # Return response with task_id
        return jsonify({"success": True, "task_id": task_id, "result": result}), 200

    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if ENABLE_TASK_DB:
    @app.route('/api/reinitiate/<task_id>', methods=['POST'])
    def reinitiate_task(task_id):
        try:
            task = get_task(task_id)
            if not task:
                return jsonify({"error": "Task not found"}), 404

            result = ir(task.payload, task.action)

            update_task_status(task_id, 'reinitiated')

            return jsonify({"success": True, "task_id": task_id, "result": result}), 200

        except Exception as e:
            logging.error(f"Server error: {str(e)}")
            return jsonify({"error": "Server error"}), 500

    @app.route('/api/tasks', methods=['GET'])
    def query_task_db():
        action = request.args.get('action')
        status = request.args.get('status')
        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')

        try:
            # Convert time strings to datetime objects if provided
            start_time = datetime.fromisoformat(
                start_time_str) if start_time_str else None
            end_time = datetime.fromisoformat(
                end_time_str) if end_time_str else None

            # Query tasks based on filters
            tasks = query_tasks(action=action, status=status,
                                start_time=start_time, end_time=end_time)

            return jsonify({"success": True, "tasks": tasks}), 200

        except Exception as e:
            logging.error(f"Server error: {str(e)}")
            return jsonify({"error": "Server error"}), 500


@app.route('/llm-planner/task', methods=['POST'])
def create_task():
    task_data = request.json
    response = task_client.create_task(task_data)
    return format_response(response)


@app.route('/llm-planner/task/<int:task_id>', methods=['GET'])
def read_task(task_id):
    response = task_client.read_task(task_id)
    return format_response(response)


@app.route('/llm-planner/task/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    update_data = request.json
    response = task_client.update_task(task_id, update_data)
    return format_response(response)


@app.route('/llm-planner/task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    response = task_client.delete_task(task_id)
    return format_response(response)


@app.route('/llm-planner/task/<int:task_id>/complete', methods=['PUT'])
def set_task_as_complete(task_id):
    response = task_client.set_task_as_complete(task_id)
    return format_response(response)


@app.route('/llm-layers/layer/<string:layer_hash>', methods=['GET'])
def get_layer(layer_hash):
    response = layer_client.get_layer(layer_hash)
    return format_response(response)


@app.route('/llm-layers/layer', methods=['POST'])
def create_layer():
    data = request.json
    response = layer_client.create_layer(data)
    return format_response(response)


@app.route('/llm-layers/layer/<string:layer_hash>', methods=['PUT'])
def update_layer(layer_hash):
    data = request.json
    response = layer_client.update_layer(layer_hash, data)
    return format_response(response)


@app.route('/llm-layers/layer/<string:layer_hash>', methods=['DELETE'])
def delete_layer(layer_hash):
    response = layer_client.delete_layer(layer_hash)
    return format_response(response)


@app.route('/llm-layers/layer/<string:layer_hash>/block_id', methods=['POST'])
def add_block_id(layer_hash):
    data = request.json
    response = layer_client.add_block_id(layer_hash, data.get("block_id"))
    return format_response(response)


@app.route('/llm-layers/layer/<string:layer_hash>/block_id', methods=['DELETE'])
def remove_block_id(layer_hash):
    data = request.json
    response = layer_client.remove_block_id(layer_hash, data.get("block_id"))
    return format_response(response)


@app.route('/llm-layers/layer/<string:layer_hash>/vdag_id', methods=['POST'])
def add_vdag_id(layer_hash):
    data = request.json
    response = layer_client.add_vdag_id(layer_hash, data.get("vdag_id"))
    return format_response(response)


@app.route('/llm-layers/layer/<string:layer_hash>/vdag_id', methods=['DELETE'])
def remove_vdag_id(layer_hash):
    data = request.json
    response = layer_client.remove_vdag_id(layer_hash, data.get("vdag_id"))
    return format_response(response)


@app.route('/llm-layers/layer/query/component_id', methods=['GET'])
def query_by_component_id():
    component_id = request.args.get("component_id")
    response = layer_client.query_by_component_id(component_id)
    return format_response(response)


@app.route('/llm-layers/layer/query/block_id_and_vdag_id', methods=['GET'])
def query_by_block_id_and_vdag_id():
    block_id = request.args.get("block_id")
    vdag_id = request.args.get("vdag_id")
    response = layer_client.query_by_block_id_and_vdag_id(block_id, vdag_id)
    return format_response(response)


@app.route('/llm-layers/layer/query', methods=['POST'])
def generic_query():
    query = request.json
    response = layer_client.generic_query(query)
    return format_response(response)


def run_app():
    app.run(port=8000, debug=True)
