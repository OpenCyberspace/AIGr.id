from flask import Flask, request, jsonify
import uuid
from .schema import PolicyRule, PolicyExecutors, Function, Graph
from .db import PolicyDB, ExecutorsDB, FunctionsDB, GraphsDB
from .executor_proxy import ExecutorProxyClient
from .jobs import JobsSubmittorClient, PolicyJobs, PolicyJobsDB
from .graph import execute_graph
from .alloc import alloc_resource_func, alloc_resource_job
from .k8s import ExecutorInitializer

import logging

app = Flask(__name__)
policy_db = PolicyDB()

def success_response(data):
    return jsonify({"success": True, "data": data})


def error_response(message):
    return jsonify({"success": False, "message": message})


@app.route("/policy", methods=["POST"])
def create_policy():
    try:
        data = request.json
        policy = PolicyRule.from_dict(data)
        success = policy_db.create(policy)
        if success:
            return jsonify({"success": True, "data": "Policy created successfully."})
        return jsonify({"success": False, "message": "Failed to create policy."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/policy/<policy_rule_uri>", methods=["GET"])
def read_policy(policy_rule_uri):
    try:
        policy = policy_db.read(policy_rule_uri)
        if policy:
            return jsonify({"success": True, "data": policy.to_dict()})
        return jsonify({"success": False, "message": "Policy not found."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/policy/<policy_rule_uri>", methods=["PUT"])
def update_policy(policy_rule_uri):
    try:
        data = request.json
        updated_policy = PolicyRule.from_dict(data)
        success = policy_db.update(policy_rule_uri, updated_policy)
        if success:
            return jsonify({"success": True, "data": "Policy updated successfully."})
        return jsonify({"success": False, "message": "Failed to update policy."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/policy/<policy_rule_uri>", methods=["DELETE"])
def delete_policy(policy_rule_uri):
    try:
        success = policy_db.delete(policy_rule_uri)
        if success:
            return jsonify({"success": True, "data": "Policy deleted successfully."})
        return jsonify({"success": False, "message": "Failed to delete policy."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/policy/query", methods=["POST"])
def query_policies():
    try:
        query_filter = request.json
        policies = policy_db.query(query_filter)
        return jsonify({"success": True, "data": [policy.to_dict() for policy in policies]})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/executor", methods=["POST"])
def create_executor():
    try:
        data = request.json
        executor = PolicyExecutors.from_dict(data)
        success = ExecutorsDB().create(executor)
        if success:
            return jsonify({"success": True, "data": "Executor created successfully."})
        return jsonify({"success": False, "message": "Failed to create executor."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/executor/<executor_id>", methods=["GET"])
def read_executor(executor_id):
    try:
        executor = ExecutorsDB().read(executor_id)
        if executor:
            return jsonify({"success": True, "data": executor.to_dict()})
        return jsonify({"success": False, "message": "Executor not found."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/executor/<executor_id>", methods=["PUT"])
def update_executor(executor_id):
    try:
        data = request.json
        updated_executor = PolicyExecutors.from_dict(data)
        success = ExecutorsDB().update(executor_id, updated_executor)
        if success:
            return jsonify({"success": True, "data": "Executor updated successfully."})
        return jsonify({"success": False, "message": "Failed to update executor."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/executor/<executor_id>", methods=["DELETE"])
def delete_executor(executor_id):
    try:
        success = ExecutorsDB().delete(executor_id)
        if success:
            return jsonify({"success": True, "data": "Executor deleted successfully."})
        return jsonify({"success": False, "message": "Failed to delete executor."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/executor/query", methods=["POST"])
def query_executors():
    try:
        query_filter = request.json
        executors = ExecutorsDB().query(query_filter)
        return jsonify({"success": True, "data": [executor.to_dict() for executor in executors]})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/executor/<executor_id>/execute_policy", methods=["POST"])
def execute_policy(executor_id):
    try:
        # Extract executor_host_uri
        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        # Initialize ExecutorProxyClient
        client = ExecutorProxyClient(base_url=executor.executor_host_uri)

        # Extract payload
        data = request.json
        policy_rule_uri = data.get("policy_rule_uri")
        input_data = data.get("input_data")
        parameters = data.get("parameters")

        if not policy_rule_uri or not input_data:
            return jsonify({"success": False, "message": "policy_rule_uri and input_data are required"}), 400

        # Execute policy
        result = client.execute_policy(policy_rule_uri, input_data, parameters)
        return jsonify({"success": True, "data": result})

    except Exception as e:
        logging.error(f"Error executing policy: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/function/deployments/create/<executor_id>", methods=["POST"])
def create_deployment(executor_id):
    try:

        if executor_id == "":
            data = request.json
            resource_allocator_policy_uri = data['alloc']['resource_allocator_policy_uri']
            settings = data['alloc']['settings']
            parameters = data['alloc']['parameters']

            executor_id, replicas = alloc_resource_func(
                resource_allocator_policy_uri, settings, parameters)
            request.json['replicas'] = replicas

            # Extract executor_host_uri
        executor = ExecutorsDB().read(executor_id)
        executor_host_uri = executor.executor_host_uri
        if not executor_host_uri:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        # Initialize ExecutorProxyClient
        client = ExecutorProxyClient(base_url=executor_host_uri)

        # Extract payload
        data = request.json
        name = data.get("name")
        policy_rule_uri = data.get("policy_rule_uri")
        policy_rule_parameters = data.get("policy_rule_parameters")
        replicas = data.get("replicas", 1)
        autoscaling = data.get("autoscaling")

        if not name or not policy_rule_uri:
            return jsonify({"success": False, "message": "name and policy_rule_uri are required"}), 400

        # Create deployment
        result = client.create_deployment(
            name, policy_rule_uri, policy_rule_parameters, replicas, autoscaling
        )

        policies_db = PolicyDB()
        result = policies_db.read(policy_rule_uri)

        # register the function:
        function = {
            "function_id": name,
            "function_executor_id": executor_id,
            "function_executor_uri": executor_host_uri,
            "function_metadata": data.get('function_metadata', {}),
            "function_tags": data.get('function_tags', []),
            "function_policy_rule_uri": policy_rule_uri,
            "function_policy_data": result.to_dict()
        }

        function_dtc = Function.from_dict(function)
        FunctionsDB().create(function_dtc)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logging.error(f"Error creating deployment: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/function/deployments/remove/<name>", methods=["DELETE"])
def remove_deployment(name):
    try:
        # Extract executor_host_uri
        function = FunctionsDB().read(name)
        executor_host_uri = function.function_executor_uri
        if not executor_host_uri:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        # Initialize ExecutorProxyClient
        client = ExecutorProxyClient(base_url=executor_host_uri)

        # Remove deployment
        result = client.remove_deployment(name)

        # also delete the entry in DB
        FunctionsDB().delete(name)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logging.error(f"Error removing deployment: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/function/call_function/<name>", methods=["POST"])
def call_function(name):
    try:
        # Extract executor_host_uri
        function = FunctionsDB().read(name)
        executor_host_uri = function.function_executor_uri
        if not executor_host_uri:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        # Initialize ExecutorProxyClient
        client = ExecutorProxyClient(base_url=executor_host_uri)

        # Extract payload
        input_data = request.json
        if not input_data:
            return jsonify({"success": False, "message": "input_data is required"}), 400

        # Call function
        result = client.call_function(name, input_data)
        return jsonify({"success": True, "data": result})

    except Exception as e:
        logging.error(f"Error calling function: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/function/<string:function_id>', methods=['GET'])
def read_function(function_id):
    try:
        function = FunctionsDB().read(function_id)
        if function:
            return jsonify({"success": True, "data": function.to_dict()}), 200
        else:
            return jsonify({"success": False, "message": "Function not found."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/function/query', methods=['POST'])
def query_functions():
    try:
        query_filter = request.json
        if not isinstance(query_filter, dict):
            return jsonify({"success": False, "message": "Invalid query filter."}), 400

        functions = FunctionsDB().query(query_filter)
        return jsonify({"success": True, "data": [function.to_dict() for function in functions]}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/graphs', methods=['POST'])
def create_graph():
    try:
        data = request.get_json()
        graph = Graph.from_dict(data)
        result = GraphsDB().create(graph)
        if result:
            return success_response({"graph_uri": graph.graph_uri})
        return error_response("Failed to create graph.")
    except Exception as e:
        return error_response(f"Error: {str(e)}")


@app.route('/graphs/<graph_uri>', methods=['GET'])
def get_graph(graph_uri):
    try:
        graph = GraphsDB().read(graph_uri)
        if graph:
            return success_response(graph.to_dict())
        return error_response(f"Graph with URI '{graph_uri}' not found.")
    except Exception as e:
        return error_response(f"Error: {str(e)}")


@app.route('/graphs/<graph_uri>', methods=['PUT'])
def update_graph(graph_uri):
    try:
        data = request.get_json()
        updated_graph = Graph.from_dict(data)
        result = GraphsDB().update(graph_uri, updated_graph)
        if result:
            return success_response({"graph_uri": graph_uri})
        return error_response(f"Failed to update graph with URI '{graph_uri}'.")
    except Exception as e:
        return error_response(f"Error: {str(e)}")


@app.route('/graphs/<graph_uri>', methods=['DELETE'])
def delete_graph(graph_uri):
    try:
        result = GraphsDB().delete(graph_uri)
        if result:
            return success_response({"graph_uri": graph_uri})
        return error_response(f"Failed to delete graph with URI '{graph_uri}'.")
    except Exception as e:
        return error_response(f"Error: {str(e)}")


@app.route('/graphs/query', methods=['POST'])
def query_graphs():
    try:
        query_filter = request.get_json()
        results = GraphsDB().query(query_filter)
        return success_response([graph.to_dict() for graph in results])
    except Exception as e:
        return error_response(f"Error: {str(e)}")


@app.route('/graph/execute_graph', methods=['POST'])
def execute_graph_api():

    try:
        data = request.get_json()
        graph_uri = data.get("graph_uri")
        input_data = data.get("input_data")

        if not graph_uri or not input_data:
            return jsonify({"success": False, "message": "Missing 'graph_uri' or 'input_data' in the request body."}), 400

        result = execute_graph(graph_uri, input_data)

        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/jobs/submit/<executor_id>", methods=['POST'])
def submit_function(executor_id: str):
    try:

        if executor_id == "":
            data = request.json
            resource_allocator_policy_uri = data['alloc']['resource_allocator_policy_uri']
            settings = data['alloc']['settings']
            parameters = data['alloc']['parameters']

            executor_id, replicas = alloc_resource_job(
                resource_allocator_policy_uri, settings, parameters)
            request.json['replicas'] = replicas

        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        executor.executor_host_uri

        base_uri = executor.executor_host_uri
        if not base_uri:
            return jsonify({"success": False, "message": "Executor host URI not found"}), 400

        # Generate a unique job ID
        job_id = str(uuid.uuid4())

        # Extract job parameters from the request body
        data = request.get_json()
        name = data.get("name")
        policy_rule_uri = data.get("policy_rule_uri")
        policy_rule_parameters = data.get("policy_rule_parameters", {})
        node_selector = data.get("node_selector", {})
        inputs = data.get("inputs", {})

        # Validate required parameters
        if not name or not policy_rule_uri:
            return jsonify({"success": False, "message": "Missing required parameters: 'name' or 'policy_rule_uri'"}), 400

        # Initialize the JobsSubmittorClient with the executor's base URI
        client = JobsSubmittorClient(api_url=base_uri)

        # Submit the job using the client
        response = client.submit_job(
            name=name,
            policy_rule_uri=policy_rule_uri,
            job_id=job_id,
            policy_rule_parameters=policy_rule_parameters,
            node_selector=node_selector,
            inputs=inputs
        )

        # Return the response to the caller
        if response.get("success"):
            return jsonify({"success": True, "job_id": job_id}), 201
        else:
            return jsonify({"success": False, "message": response.get("message", "Unknown error")}), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    try:
        job = PolicyJobsDB().read(job_id)
        if job:
            return success_response(job.to_dict())
        return error_response(f"Job with ID '{job_id}' not found.")
    except Exception as e:
        return error_response(f"Error: {str(e)}")


@app.route('/jobs/query', methods=['POST'])
def query_jobs():
    try:
        query_filter = request.get_json()
        if not isinstance(query_filter, dict):
            return error_response("Invalid query filter format.")
        results = PolicyJobsDB().query(query_filter)
        return success_response([job.to_dict() for job in results])
    except Exception as e:
        return error_response(f"Error: {str(e)}")


@app.route("/executor/<executor_id>/create-infra", methods=["POST"])
def create_infra(executor_id):
    try:
        data = request.json
        initializer = ExecutorInitializer(**data, executor_id=executor_id)
        initializer.create_executor()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/executor/<executor_id>/remove-infra", methods=["DELETE"])
def remove_infra(executor_id):
    try:
        data = request.json
        initializer = ExecutorInitializer(**data, executor_id=executor_id)
        initializer.remove_executor()
        return jsonify({"success": True, "data": "Created infra"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/jobs/submit-with-estimate/<executor_id>', methods=['POST'])
def create_job_with_estimate(executor_id):
    try:
        data = request.json

        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        executor.executor_host_uri

        base_uri = executor.executor_host_uri
        if not base_uri:
            return jsonify({"success": False, "message": "Executor host URI not found"}), 400

        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        executor.executor_host_uri

        base_uri = executor.executor_host_uri
        if not base_uri:
            return jsonify({"success": False, "message": "Executor host URI not found"}), 400

        executor_client = ExecutorProxyClient(base_uri)

        result = executor_client.create_job_with_estimate(
            name=data["name"],
            policy_rule_uri=data["policy_rule_uri"],
            job_id=data["job_id"],
            policy_rule_parameters=data.get("policy_rule_parameters"),
            inputs=data.get("inputs", {})
        )
        return success_response(result)
    except Exception as e:
        return error_response(str(e))


@app.route('/executor/<executor_id>/estimator/estimate', methods=['POST'])
def estimate_deployment(executor_id):
    try:
        data = request.json

        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        executor.executor_host_uri

        base_uri = executor.executor_host_uri
        if not base_uri:
            return jsonify({"success": False, "message": "Executor host URI not found"}), 400

        executor_client = ExecutorProxyClient(base_uri)

        result = executor_client.estimate_deployment(
            mode=data["mode"],
            policy=data["policy"] if data["mode"] == "adhoc" else data["policy_rule_uri"]
        )
        return success_response(result)
    except Exception as e:
        return error_response(str(e))


@app.route('/function/deployments/create-with-estimate/<executor_id>', methods=['POST'])
def create_deployment_with_estimate(executor_id):
    try:
        data = request.json

        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        executor.executor_host_uri

        base_uri = executor.executor_host_uri
        if not base_uri:
            return jsonify({"success": False, "message": "Executor host URI not found"}), 400

        executor_client = ExecutorProxyClient(base_uri)

        result = executor_client.create_deployment_with_estimate(
            name=data["name"],
            policy_rule_uri=data["policy_rule_uri"],
            policy_rule_parameters=data.get("policy_rule_parameters"),
            replicas=data.get("replicas", 1),
            autoscaling=data.get("autoscaling")
        )
        return success_response(result)
    except Exception as e:
        return error_response(str(e))


@app.route("/graph/estimate-adhoc-graph/<executor_id>")
def estimate_graph_adhoc(executor_id: str):
    try:

        policies = request.json['policies']
        # call estimate for each node:
        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        executor.executor_host_uri

        base_uri = executor.executor_host_uri
        if not base_uri:
            return jsonify({"success": False, "message": "Executor host URI not found"}), 400

        executor_client = ExecutorProxyClient(base_uri)
        response = executor_client.estimate_graph(policies)
        return {"success": True, "data": response}

    except Exception as e:
        return error_response(str(e))


@app.route("/graph/deploy-adhoc-graph/<executor_id>")
def deploy_adhoc_graph(executor_id: str):
    try:

        data = request.json

        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        executor.executor_host_uri

        base_uri = executor.executor_host_uri
        if not base_uri:
            return jsonify({"success": False, "message": "Executor host URI not found"}), 400

        executor_client = ExecutorProxyClient(base_uri)
        executor_client.deploy_adhoc_graph(
            policy_db, graph_db=GraphsDB(), data=data)

        return {"success": True, "data": "graph created"}

    except Exception as e:
        return error_response(str(e))


@app.route("/graph/remove/<executor_id>")
def remove_executor(executor_id: str):
    try:

        graph_uri = request.args.get('graph_uri')

        executor = ExecutorsDB().read(executor_id)
        if not executor:
            return jsonify({"success": False, "message": "Executor not found"}), 404

        executor.executor_host_uri

        base_uri = executor.executor_host_uri
        if not base_uri:
            return jsonify({"success": False, "message": "Executor host URI not found"}), 400

        executor_client = ExecutorProxyClient(base_uri)
        executor_client.remove_adhoc_graph(
            policy_db, graph_db=GraphsDB(), graph_uri=graph_uri
        )

        return {"success": True, "data": "graph removed"}

    except Exception as e:
        return error_response(str(e))


def run_app():
    app.run(host='0.0.0.0', port=10000)
