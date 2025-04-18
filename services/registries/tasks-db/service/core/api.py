from flask import Flask, request, jsonify
from .crud import GlobalTasksDatabase
from .schema import GlobalTask
from .redis_pusher import UpdatesRedisPusher
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)
task_db = GlobalTasksDatabase()


redis_pusher = UpdatesRedisPusher()


@app.route('/task', methods=['POST'])
def create_task():
    try:
        task_data = request.json
        task = GlobalTask.from_dict(task_data)
        success, result = task_db.insert(task)
        if success:
            return jsonify({"success": True, "data": {"message": "Task created", "task_id": str(result)}}), 200
        else:
            return jsonify({"success": False, "message": result}), 400
    except Exception as e:
        logger.error(f"Error in create_task: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/task/<string:task_id>', methods=['GET'])
def get_task(task_id):
    try:
        success, result = task_db.get_by_task_id(task_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "message": result}), 404
    except Exception as e:
        logger.error(f"Error in get_task: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/task/<string:task_id>', methods=['PUT'])
def update_task(task_id):
    try:
        update_data = request.json
        success, result = task_db.update(task_id, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Task updated", "modified_count": result}}), 200
        else:
            return jsonify({"success": False, "message": result}), 400
    except Exception as e:
        logger.error(f"Error in update_task: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/task/<string:task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        success, result = task_db.delete(task_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Task deleted"}}), 200
        else:
            return jsonify({"success": False, "message": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_task: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/tasks', methods=['GET'])
def get_tasks_by_task_type():
    try:
        task_type = request.args.get('task_type')
        task_status = request.args.get('task_status')
        success, result = task_db.get_tasks_by_task_type(
            task_type, task_status)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "message": result}), 404
    except Exception as e:
        logger.error(f"Error in get_tasks_by_task_type: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/task_update', methods=['POST'])
def push_task_update():
    try:
        update_data = request.json
        task_id = update_data.get("task_id")
        status = update_data.get("status")
        task_status_data = update_data.get("task_status_data", {})

        if not task_id or not status:
            return jsonify({"success": False, "message": "task_id and status are required"}), 400

        redis_pusher.push_update(task_id, status, task_status_data)
        return jsonify({"success": True, "message": "Task update pushed successfully"}), 200
    except Exception as e:
        logger.error(f"Error in push_task_update: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


def run_server(port = 8000):
    app.run(host='0.0.0.0', port=port)