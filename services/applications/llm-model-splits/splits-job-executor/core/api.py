from flask import Flask, request, jsonify
import logging

from .k8s import start_new_job

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


@app.route("/start_model_split_job", methods=["POST"])
def start_model_split_job():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No input data provided"}), 400

        task_data = data.get("task_data")
        container_image = data.get("container_image")
        storage_size = data.get("storage_size", "1Gi")

        if not task_data or not container_image:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        task_type = "model_splits"
        task_id = start_new_job(task_type, task_data, container_image, storage_size)

        return jsonify({
            "success": True,
            "task_id": task_id
        })

    except Exception as e:
        logging.exception("Failed to start model split job")
        return jsonify({"success": False, "error": str(e)}), 500



def run_server():
    app.run(host="0.0.0.0", port=5000)
