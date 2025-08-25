import threading
import redis
import json
import os
import time
import requests
import logging
from flask import Flask, request, jsonify

from .policy_sandbox import LocalPolicyEvaluator
from .block import BlocksDB
from .metrics_api import get_metrics_collector

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


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
            logging.info("Successfully loaded block data.")
            return True, result
        else:
            logging.error(f"Failed to load block data: {result}")
            return False, result

    except Exception as e:
        logging.error(f"Exception while loading block data: {e}")
        return False, str(e)


class BlockHealthChecker:
    def __init__(self) -> None:
        self.current_instances = {}
        time.sleep(15)

        ret, block_data = load_block_data()
        if not ret:
            raise Exception(f"Failed to get block data, error={block_data}")

        self.block_id = os.getenv("BLOCK_ID")
        self.metrics_collector = get_metrics_collector(self.block_id)

        self.block_data = block_data
        # Init load balancer
        self.stability_checker = None
        policies = self.block_data.get("policies", {})

        if "stabilityChecker" in policies:
            sc_settings = policies["stabilityChecker"].get("settings", {})
            sc_parameters = policies["stabilityChecker"].get("parameters", {})
            sc_policy_rule_uri = policies["stabilityChecker"].get(
                "policyRuleURI", {})

            sc_settings.update({"block_data": self.block_data})
            sc_settings.update({"cluster_data": self.block_data.get('cluster')})
            sc_settings.update({"get_metrics": self.metrics_collector})

            self.stability_checker = LocalPolicyEvaluator(
                sc_policy_rule_uri, sc_parameters, sc_settings
            )

            self.health_check_interval = int(
                policies.get('stabilityChecker', {})
                .get('settings', {})
                .get('health_check_interval', 30) or 30
            )

            logging.info(
                f"Health check interval set to {self.health_check_interval} seconds.")

        self.instance_listener = redis.Redis(
            host="localhost", port=6379, db=0, password=None
        )

        # Start the listener thread for instance changes
        threading.Thread(
            target=self.listen_for_instance_changes, daemon=True
        ).start()

    def listen_for_instance_changes(self):
        while True:
            try:
                _, message = self.instance_listener.brpop(
                    "K8s_POD_LIST_HEALTH_CHECKER")
                c_i = json.loads(message)
                self.current_instances = c_i["data"]
                logging.info(
                    f"Updated current_instances: {len(self.current_instances)} instances.")
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON message: {e}")
            except redis.RedisError as e:
                logging.error(f"Redis error: {e}")
            except Exception as e:
                logging.error(f"Unexpected error in instance listener: {e}")

    def check_health_of_instance(self, url):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            response.raise_for_status()
            json_response = response.json()

            if json_response.get("success"):
                return json_response.get("data")
            else:
                logging.warning(f"Instance {url} failed health check.")
                return {"success": False, "message": "Health check failed"}
        except requests.exceptions.Timeout:
            logging.error(f"Timeout error while checking health for {url}")
            return {"success": False, "message": "Timeout error"}
        except requests.exceptions.RequestException as e:
            logging.error(
                f"Request error while checking health for {url}: {e}")
            return {"success": False, "message": str(e)}
        except Exception as e:
            logging.error(
                f"Unexpected error during health check for {url}: {e}")
            return {"success": False, "message": str(e)}

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

                logging.info(
                    f"Received management command: {mgmt_action} with data: {mgmt_data}")
                result = self.stability_checker.execute_mgmt_command(mgmt_action, mgmt_data)

                return jsonify({"success": True, "data": result}), 200

            except Exception as e:
                logging.error(f"Error handling management request: {e}")
                return jsonify({"success": False, "message": str(e)}), 500

        self.management_server_thread = threading.Thread(
            target=app.run, kwargs={"host": "0.0.0.0", "port": 19001})
        self.management_server_thread.daemon = True
        self.management_server_thread.start()

    def start_health_checks(self):
        if not self.stability_checker:
            logging.info(
                "Stability checker not configured for this block. Sleeping indefinitely.")
            while True:
                time.sleep(1000)

        logging.info("Starting health check loop...")

        while True:
            try:
                health_check_data = {}
                for instance_id, pod_data in self.current_instances.items():

                    status = pod_data.get("status", {}) or {}

                    skip_healthcheck = False
                    for cstatus in status.get("container_statuses", []) or []:
                        state = cstatus.get("state", {})
                        if state.get("waiting"):   # means image pull / creating
                            reason = state["waiting"].get("reason", "Unknown")
                            print(f"[{instance_id}] skipping health check (container waiting: {reason})")
                            skip_healthcheck = True
                            break

                    if skip_healthcheck:
                        health_check_data[instance_id] = True
                        continue

                    pod_ip = (
                        status.get("pod_ip")
                        or status.get("podIP")
                        or (status.get("pod_ips") and status["pod_ips"][0].get("ip"))          # some clients
                        or (status.get("pod_i_ps") and status["pod_i_ps"][0].get("ip"))        # others (as in your dump)
                    )

                    if pod_ip:
                        url = f"http://{pod_ip}:18001"
                        health_status = self.check_health_of_instance(url)

                        logging.info(f"instance_id={instance_id} health_data={health_status}")

                        if 'status' in health_status and health_status['status'] == "healthy":
                            health_check_data[instance_id] = True
                        else:
                            health_check_data[instance_id] = False
                    else:
                        logging.warning(
                            f"Instance {instance_id} has no pod IP.")
                        health_check_data[instance_id] = False

                # Execute stability policy rule
                logging.info("Executing stability policy rule.")
                self.stability_checker.execute_policy_rule(
                    input_data={
                        "block_data": self.block_data,
                        "cluster_data": self.block_data['cluster'],
                        "health_check_data": health_check_data,
                        "instances": self.current_instances}
                )

            except Exception as e:
                logging.error(f"Error in health check loop: {e}")

            logging.info(
                f"Sleeping for {self.health_check_interval} seconds before next health check.")
            time.sleep(self.health_check_interval)


def run_health_checker():
    try:

        health_checker = BlockHealthChecker()
        health_checker.run_management_server()
        health_checker.start_health_checks()

    except Exception as e:
        logging.error(f"health checker failed: {e}")
