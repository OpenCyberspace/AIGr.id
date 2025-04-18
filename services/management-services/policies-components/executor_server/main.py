from core.executor import PolicyFunctionExecutor
import os
from flask import Flask, request, jsonify
import json

def init_function_executor():
    try:

        policy_rule_uri = os.getenv("POLICY_RULE_URI")
        optional_parameters = os.getenv("POLICY_RULE_PARAMETERS", None)

        if optional_parameters:
            optional_parameters = json.loads(optional_parameters)

        executor = PolicyFunctionExecutor(policy_rule_uri, optional_parameters)

        return executor

    except Exception as e:
        raise e


executor = init_function_executor()

app = Flask(__name__)


@app.post("/execute")
def execute():
    try:

        input_data = request.get_json()
        result = executor.execute(input_data)

        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
