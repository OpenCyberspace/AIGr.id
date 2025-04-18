import os
import logging
from flask import Flask, request, jsonify
from .policy_sandbox import LocalPolicyEvaluator

app = Flask(__name__)


@app.post("/executeFailurePolicy")
def execute_failure_policy():
    try:
        api_url = os.getenv("POLICY_EXECUTOR_API_URL")
        if not api_url:
            logging.error("POLICY_EXECUTOR_API_URL environment variable not set.")
            return jsonify({"success": False, "message": "API URL not configured"}), 500

        data = request.get_json()
        failure_policy_id = data.get("failure_policy_id")
        inputs = data.get("inputs")
        parameters = data.get("parameters")

        if not failure_policy_id or inputs is None or parameters is None:
            logging.error("Missing required parameters in request data.")
            return jsonify({"success": False, "message": "Missing required parameters"}), 400

        executor = LocalPolicyEvaluator(
            failure_policy_id, parameters, {}, custom_class=None)
        result = executor.execute(inputs)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def run_app():
    app.run(host="0.0.0.0", port=5000)
