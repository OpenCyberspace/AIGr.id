import os
from flask import Flask, request, jsonify
import redis
import json
import logging
import threading

from .processor import DryRunner
from .global_tasks import GlobalTasksDB

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection wrapper
class RedisClient:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_HOST_URL", 'redis://localhost:6379/0')
        self.client = None
        self.connect()

    def connect(self):
        try:
            self.client = redis.StrictRedis.from_url(self.redis_url, socket_connect_timeout=5)
            self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    def push(self, key, value):
        try:
            if not self.client:
                self.connect()
            self.client.rpush(key, value)
        except redis.exceptions.ConnectionError as ce:
            logger.warning(f"Redis connection lost. Reconnecting...: {ce}")
            self.connect()
            self.push(key, value)
        except Exception as e:
            logger.error(f"Error pushing to Redis: {e}")
            raise e

# Initialize Redis client wrapper
redis_wrapper = RedisClient()


def handle_request(method, input_data):
    try:
        result = method(input_data)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/submitTask', methods=['POST'])
def submit_task():
    try:
        task_data = request.get_json()
        if not task_data:
            raise ValueError("No JSON data provided")

        vdag_name = task_data.get('vdag_name', '')
        vdag_version = task_data.get('vdag_version', {'version': '', 'release-tag': ''})
        vdagURI = f"{vdag_name}:{vdag_version.get('version', '')}-{vdag_version.get('release-tag', '')}" \
            if vdag_name and vdag_version.get('version') and vdag_version.get('release-tag') else ''

        global_tasks_db = GlobalTasksDB()
        task_id = global_tasks_db.create_task(task_type="vdag_processing", task_data=task_data, task_status="pending")

        task_json = json.dumps({
            "task_id": task_id,
            "task_data": task_data
        })

        redis_wrapper.push('INPUTS', task_json)

        logger.info("Task submitted successfully")
        return jsonify({"success": True, "data": {"vdagURI": vdagURI, "task_id": task_id}}), 200

    except Exception as e:
        logger.error(f"Error submitting task: {e}")
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/dryrun/assignment-policy", methods=["POST"])
def dryrun_assignment_policy():
    input_data = request.get_json()
    return handle_request(DryRunner.DryRunAssignmentPolicy, input_data)


@app.route("/dryrun/end-to-end", methods=["POST"])
def dryrun_end_to_end():
    input_data = request.get_json()
    return handle_request(DryRunner.DryRunEndToEnd, input_data)


@app.route("/dryrun/validate-graph", methods=["POST"])
def validate_graph():
    input_data = request.get_json()
    return handle_request(DryRunner.ValidateGraph, input_data)


def run_server_thread():
    server_thread = threading.Thread(
        target=app.run, kwargs={'debug': False, 'use_reloader': False, 'port': 10500, 'host': '0.0.0.0'})
    server_thread.start()
    return server_thread
