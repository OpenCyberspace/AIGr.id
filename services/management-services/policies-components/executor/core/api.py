from flask import Flask, request, jsonify
import requests
import os
from .executor import MultiprocessingPolicyRuleExecutor
from .function_infra import PolicyFunctionInfra
from .job_infra import PolicyJobInfra
from .output_listener import start_output_listener
from .db import PolicyDB, PolicyRule
from .estimator import ResourceEstimator

import logging

app = Flask(__name__)

policy_executor = MultiprocessingPolicyRuleExecutor()
policy_db = PolicyDB()

namespace = "policies"
default_port = 5000


@app.route('/execute_policy', methods=['POST'])
def execute_policy():

    try:
        # Parse the incoming JSON request
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Invalid or missing JSON body"}), 400

        # Validate required fields
        policy_rule_uri = data.get("policy_rule_uri")
        input_data = data.get("input_data")
        parameters = data.get("parameters", None)  # Optional

        if not policy_rule_uri or not input_data:
            return jsonify({
                "success": False,
                "message": "Missing required fields: 'policy_rule_uri' and/or 'input_data'."
            }), 400

        # Execute the policy
        result_queue = policy_executor.execute(
            policy_rule_uri, parameters, input_data)

        output = result_queue.get()

        return jsonify({
            "success": True,
            "data": output
        }), 202

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/deployments', methods=['POST'])
def create_deployment():

    try:
        data = request.get_json()
        name = data['name']
        policy_rule_uri = data['policy_rule_uri']
        policy_rule_parameters = data.get('policy_rule_parameters', None)
        replicas = data.get('replicas', 1)
        autoscaling = data.get('autoscaling', None)

        PolicyFunctionInfra().create_deployment(
            name=name,
            policy_rule_uri=policy_rule_uri,
            policy_rule_parameters=policy_rule_parameters,
            replicas=replicas,
            autoscaling=autoscaling,
            node_id=None
        )

        return jsonify({"success": True, "message": f"Deployment '{name}' created successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/estimator/estimate', methods=['POST'])
def estimate_deployment():

    try:

        input_data = request.json
        estimate_type = input_data.get('estimate_type', 'deployment')
        policy_rule = {}
        if input_data['mode'] == "adhoc":
            input_data = input_data['policy']
            policy_rule = PolicyRule.from_dict(input_data)
        else:
            input_data = input_data['policy_rule_uri']
            policy_rule = policy_db.read(input_data)

        allowed, node_id = ResourceEstimator().estimate(
            input_policy_rule=policy_rule, type_=estimate_type
        )

        if not allowed:
            return jsonify({"success": False, "error": "policy rule not allowed to be executed by estimator"})

        return jsonify({"success": True, "data": {"allowed": allowed, "node_id": node_id}}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/deployments/deploy-with-estimate', methods=['POST'])
def create_deployment_with_estimate():

    try:

        input_data = request.json

        policy_rule = policy_db.read(input_data['policy_rule_uri'])

        allowed, node_id = ResourceEstimator().estimate(input_policy_rule=policy_rule)
        if not allowed:
            return jsonify({"success": False, "error": "policy rule not allowed to be executed by estimator"})

        node_selector = {"nodeID": node_id}

        name = input_data['name']
        policy_rule_uri = input_data['policy_rule_uri']
        policy_rule_parameters = input_data.get('policy_rule_parameters', None)
        replicas = input_data.get('replicas', 1)
        autoscaling = input_data.get('autoscaling', None)

        PolicyFunctionInfra().create_deployment(
            name=name,
            policy_rule_uri=policy_rule_uri,
            policy_rule_parameters=policy_rule_parameters,
            replicas=replicas,
            autoscaling=autoscaling,
            node_selector=node_selector
        )

        return jsonify({"success": True, "message": f"Deployment '{name}' created successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/deployments/<string:name>', methods=['DELETE'])
def remove_deployment(name):

    try:
        PolicyFunctionInfra().remove_deployment(name=name)
        return jsonify({"success": True, "message": f"Deployment '{name}' removed successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/call_function/<name>', methods=['POST'])
def call_function(name):

    try:
        service_url = f"http://{name}-svc.{namespace}.svc.cluster.local:{default_port}/execute"

        input_data = request.get_json()
        response = requests.post(service_url, json=input_data)

        return jsonify(response.json()), response.status_code

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/create_job', methods=['POST'])
def create_job_endpoint():
    try:
        data = request.get_json()
        name = data['name']
        policy_rule_uri = data['policy_rule_uri']
        job_id = data['job_id']
        redis_host = os.getenv("JOB_MANAGER_URL", "localhost")
        redis_queue_name = "JOB_OUTPUTS"
        policy_rule_parameters = data.get('policy_rule_parameters', None)
        node_selector = data.get('node_selector', None)
        inputs = data.get('inputs', {})

        job_manager = PolicyJobInfra()

        job_manager.create_job(
            name=name,
            policy_rule_uri=policy_rule_uri,
            job_id=job_id,
            redis_host=redis_host,
            redis_queue_name=redis_queue_name,
            policy_rule_parameters=policy_rule_parameters,
            node_selector=node_selector,
            inputs=inputs
        )

        return jsonify({"success": True, "message": f"Job '{name}' created successfully."}), 201
    except Exception as e:
        logging.error(f"Error in create_job endpoint: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/create_job_with_estimate', methods=['POST'])
def create_job_with_estimate():
    try:

        # run estimate
        input_data = request.get_json()
        input_data = request.json

        policy_rule = policy_db.read(input_data['policy_rule_uri'])

        allowed, node_id = ResourceEstimator().estimate(input_policy_rule=policy_rule, type_="job")
        if not allowed:
            return jsonify({"success": False, "error": "policy rule not allowed to be executed by estimator"})

        node_selector = {"nodeID": node_id}
        name = input_data['name']
        policy_rule_uri = input_data['policy_rule_uri']
        job_id = input_data['job_id']
        redis_host = os.getenv("JOB_MANAGER_URL", "localhost")
        redis_queue_name = "JOB_OUTPUTS"
        policy_rule_parameters = input_data.get('policy_rule_parameters', None)
        inputs = input_data.get('inputs', {})

        job_manager = PolicyJobInfra()

        job_manager.create_job(
            name=name,
            policy_rule_uri=policy_rule_uri,
            job_id=job_id,
            redis_host=redis_host,
            redis_queue_name=redis_queue_name,
            policy_rule_parameters=policy_rule_parameters,
            node_selector=node_selector,
            inputs=inputs
        )

        return jsonify({"success": True, "message": f"Job '{name}' created successfully."}), 201
    except Exception as e:
        logging.error(f"Error in create_job endpoint: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


def run_app():
    start_output_listener()
    app.run(host='0.0.0.0', port=10250)
