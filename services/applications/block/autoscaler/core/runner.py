import time
import os
import redis
import logging
import json
import threading

from .controller import ClusterControllerExecutor
from .blocks import BlocksDB, ClustersDB
from .policy_sandbox import LocalPolicyEvaluator
from .default_policies import DefaultAutoscalerPolicy
from flask import request, Flask, jsonify
from threading import Thread

from .metrics import get_metrics_collector

logging.basicConfig(level=logging.INFO)


class AutoscalerRunner:

    def __init__(self) -> None:
        try:
            logging.info("Initializing AutoscalerRunner")
            self.block_id = os.getenv("BLOCK_ID")
            self.cluster_id = os.getenv("CLUSTER_ID", "cluster-123")

            self.controller_client = ClusterControllerExecutor()
            self.sleep_interval = 0

            self.block_data = None
            self.cluster_data = None

            self.auto_scaler = None

            self._load_block_and_cluster_data()

            self.auto_scaler = None

            self._load_policy_rule()

            self.instance_listener = redis.Redis(
            host='localhost', port=6379, db=0, password=None)

            threading.Thread(target=self.listen_for_instance_changes, daemon=True).start()

        except Exception as e:
            logging.error(f"Error during initialization: {e}")
            raise e

    def _load_policy_rule(self):
        try:
            logging.info("Loading policy rule")
            policies = self.block_data.get('policies', {})
            if 'autoscaler' in policies:
                autoscaler_settings = policies['autoscaler'].get(
                    'settings', {})
                autoscaler_parameters = policies['autoscaler'].get(
                    'parameters', {})
                autoscaler_policy_rule_uri = policies['autoscaler'].get(
                    "policyRuleURI", {})

                autoscaler_settings["get_metrics"] = get_metrics_collector(
                    self.block_id
                )

                self.auto_scaler = LocalPolicyEvaluator(
                    autoscaler_policy_rule_uri,
                    parameters=autoscaler_parameters,
                    settings=autoscaler_settings
                )

                self.sleep_interval = int(
                    autoscaler_settings.get('intervalSeconds', 30)
                )

        except Exception as e:
            logging.error(f"Error loading policy rule: {e}")
            raise e

    def _load_block_and_cluster_data(self):
        try:
            logging.info("Loading block and cluster data")
            ret, resp = BlocksDB().get_block_by_id(self.block_id)
            if not ret:
                raise Exception(str(resp))
            self.block_data = resp

            ret, resp = ClustersDB().get_cluster_by_id(self.cluster_id)
            if not ret:
                raise Exception(str(resp))
            self.cluster_data = resp

        except Exception as e:
            logging.error(f"Error loading block and cluster data: {e}")
            raise e

    def _handle_autoscaler_result(self, resp):
        try:
            logging.info(f"Handling autoscaler result: {resp}")
            if not resp['skip']:
                operation = resp.get('operation', "scale")

                payload = {}
                
                if operation == "upscale":
                    payload['block_id'] = self.block_id
                    payload['operation'] = "scale"
                    payload['instances_count'] = resp.get('instances_count', 0)
                    if payload['instances_count'] == 0:
                        return

                    # check if the block has provided optional allocation data:
                    if 'allocation_data' in resp:
                        payload['allocation_data'] = resp['allocation_data']
                    
                elif operation == "downscale":

                    payload['block_id'] = self.block_id
                    payload['instances_list'] = resp.get('instances_list', [])
                    payload['operation'] = "downscale"
                
                else:
                    raise Exception("invalid action {}".format(operation))

                resp = self.controller_client.scale_instance(payload)
                if not resp['success']:
                    raise Exception(str(resp['data']))

        except Exception as e:
            logging.error(f"Error handling autoscaler result: {e}")
            raise e

    def run_autoscaler_iteration(self):
        try:
            logging.info("Running autoscaler iteration")

            # get current instances list:
            resp = self.auto_scaler.execute_policy_rule({
                "block_data": self.block_data,
                "cluster_data": self.cluster_data,
                "current_instances": self.current_instances
            })

            self._handle_autoscaler_result(resp)

            return True, "processed"

        except Exception as e:
            logging.error(f"Error running autoscaler iteration: {e}")
            return False, str(e)

    def listen_for_instance_changes(self):
        while True:
            try:
                _, message = self.instance_listener.brpop(
                    "K8s_POD_LIST_AUTOSCALER")
                c_i = json.loads(message)
                self.current_instances = c_i["ids"]

                if 'executor' in self.current_instances:
                    self.current_instances.remove("executor")

                logging.info(f"Updated current_instances: {self.current_instances}")
            except Exception as e:
                logging.error(f"auto scaler instance update error: {e}")

    def run_autoscaler_iterations(self):
        logging.info("Starting autoscaler iterations")
        # initial sleep for 60s
        time.sleep(60)

        while True:
            try:
                self.run_autoscaler_iteration()
                time.sleep(self.sleep_interval)
            except Exception as e:
                logging.error(f"Error in autoscaler iterations loop: {e}")
    

    def run_management_server(self):
        app = Flask(__name__)

        @app.route("/mgmt", methods=["POST"])
        def handle_mgmt():
            try:
                payload = request.json
                mgmt_action = payload.get("mgmt_action")
                mgmt_data = payload.get("mgmt_data", {})

                if not mgmt_action:
                    return jsonify({"success": False, "message": "mgmt_action is required"}), 400

                logging.info(f"Received management command: {mgmt_action} with data: {mgmt_data}")
                result = self.auto_scaler.execute_mgmt_command(mgmt_action, mgmt_data)

                return jsonify({"success": True, "data": result}), 200

            except Exception as e:
                logging.error(f"Error handling management request: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        self.management_server_thread = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 10000})
        self.management_server_thread.daemon = True
        self.management_server_thread.start()



def run_autoscaler():
    try:
        logging.info("Starting autoscaler")
        autoscaler = AutoscalerRunner()
        autoscaler.run_management_server()
        autoscaler.run_autoscaler_iterations()
    except Exception as e:
        logging.error(f"Error running autoscaler: {e}")
