import os
import redis
import json
import time
import threading
import logging


from .globals import init_internal_queue, init_receiver_queue, get_internal_queue
from .block import BlocksDB
from .policy_sandbox import LocalPolicyEvaluator
from .server import serve_in_thread
from .metrics_api import get_metrics_collector
from .default_policies import LoadBalancerPolicyRule

from flask import Flask, request, jsonify
from threading import Thread


def load_block_data():
    try:
        base_url = os.getenv("BLOCKS_DB_URI", "http://localhost:3001")
        if not base_url:
            raise ValueError("BLOCKS_DB_URI environment variable is not set.")

        db = BlocksDB(base_url)

        block_id = os.getenv("BLOCK_ID")
        if not block_id:
            raise ValueError("BLOCK_ID environment variable is not set.")

        success, result = db.get_block_by_id(block_id)
        if success:
            return True, result
        else:
            return False, result

    except Exception as e:
        return False, str(e)


class ConnectionsCache:
    def __init__(self):
        self.connections = {}
        self.mode = os.getenv("MODE", "prod")

    def get_connection(self, instance_id: str) -> redis.Redis:
        if instance_id in self.connections:
            return self.connections[instance_id]
        else:
            block_id = os.getenv("BLOCK_ID")

            url = f"{block_id}-{instance_id}-svc.blocks.svc.cluster.local"

            if self.mode == "test":
                url = "localhost"

            new_connection = redis.Redis(
                host=url, port=6379, db=0, password=None)
            self.connections[instance_id] = new_connection
            return new_connection


class Executor:

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        init_internal_queue()
        self.block_id = os.getenv("BLOCK_ID")
        self.connections = ConnectionsCache()

        self.metrics_collector = get_metrics_collector(self.block_id)

        time.sleep(15)

        init_receiver_queue()
        ret, block_data = load_block_data()
        if not ret:
            raise Exception(f"failed to get block data, error={block_data}")

        self.block_data = block_data
        # init load balancer:
        self.load_balancer = None
        policies = self.block_data.get('policies', {})
        if 'loadBalancer' in policies:
            lb_settings = policies['loadBalancer'].get('settings', {})
            lb_parameters = policies['loadBalancer'].get('parameters', {})
            lb_policy_rule_uri = policies['loadBalancer'].get(
                "policyRuleURI", {})

            lb_settings.update({
                "get_metrics": self.metrics_collector
            })

            self.load_balancer = LocalPolicyEvaluator(
                lb_policy_rule_uri, lb_parameters, lb_settings, custom_class=LoadBalancerPolicyRule)

        self.current_instances = []
        self.instance_listener = redis.Redis(
            host='localhost', port=6379, db=0, password=None)

        threading.Thread(
            target=self.listen_for_instance_changes, daemon=True).start()

    def listen_for_instance_changes(self):
        while True:
            try:
                _, message = self.instance_listener.brpop(
                    "K8s_POD_LIST_EXECUTOR")
                c_i = json.loads(message)
                self.current_instances = c_i["ids"]
                self.logger.info(
                    f"Updated current_instances: {self.current_instances}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode JSON message: {e}")
            except redis.RedisError as e:
                self.logger.error(f"Redis error: {e}")

    def process_adhoc_jobs(self):

        _, queue = get_internal_queue()
        ip_queue = self.block_id + "_inputs"

        while True:
            try:

                data = queue.wait_and_get()
                packet = data['packet']
                raw = data['raw']

                # use load balancer to select the target instance:
                if self.load_balancer:
                    resp = self.load_balancer.execute_policy_rule({
                        "mode": "load_balance",
                        "packet": packet,
                        "instances": self.current_instances
                    })

                    target_instance = resp['instance_id']
                    connection = self.connections.get_connection(
                        target_instance)
                    connection.lpush(ip_queue, raw)
                else:
                    target_instance = "1"
                    connection = self.connections.get_connection(
                        target_instance)
                    connection.lpush(ip_queue, raw)

            except Exception as e:
                self.logger.error(f"failed to process frame: {e}")

    def run_management_server(self):
        app = Flask(__name__)

        @app.route("/mgmt", methods=["POST"])
        def handle_mgmt():
            try:
                payload = request.json
                mgmt_action = payload.get("mgmt_action")
                mgmt_data = payload.get("mgmt_data", {})

                # handle executor management commands:
                if mgmt_action == "estimate":
                    estimate_data = self.load_balancer.execute_policy_rule({
                        "mode": "estimate"
                    })

                    return jsonify({"success": True, "data": estimate_data}), 200

                if mgmt_action == "check_execute":
                    check_execute_data = self.load_balancer.execute_policy_rule({
                        "mode": "check_execute",
                        "inputs": mgmt_data
                    })

                    return jsonify({"success": True, "data": check_execute_data}), 200

                if mgmt_action == "health_check":
                    health_check_data = self.load_balancer.execute_policy_rule({
                        "mode": "health_check",
                        "inputs": {}
                    })

                    return jsonify({"success": True, "data": health_check_data}), 200

                if not mgmt_action:
                    return jsonify({"success": False, "message": "mgmt_action is required"}), 400

                logging.info(
                    f"Received management command: {mgmt_action} with data: {mgmt_data}")
                result = self.load_balancer.execute_mgmt_command(
                    mgmt_action, mgmt_data)

                return jsonify({"success": True, "data": result}), 200

            except Exception as e:
                logging.error(f"Error handling management request: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        self.management_server_thread = Thread(
            target=app.run, kwargs={"host": "0.0.0.0", "port": 18001})
        self.management_server_thread.daemon = True
        self.management_server_thread.start()


def runner():
    while True:
        try:

            serve_in_thread()

            executor = Executor()

            executor.run_management_server()
            executor.process_adhoc_jobs()

        except Exception as e:
            logging.error(f"failed to run the instance, error={e}")
            time.sleep(5)
