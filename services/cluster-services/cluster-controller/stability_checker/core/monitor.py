import os
import threading
import time
import logging

from .cluster import ClusterClient
from .policy_sandbox import LocalPolicyEvaluator
from .client import NodesAPIClient


# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClusterStabilityCheckerPolicyExecutor:

    def __init__(self) -> None:
        logger.info("Initializing ClusterStabilityCheckerPolicyExecutor")
        cluster_id = os.getenv("CLUSTER_ID")
        if not cluster_id:
            logger.error("CLUSTER_ID not specified in the environment")
            raise Exception("CLUSTER_ID not specified in the env")

        logger.info(f"Fetching cluster data for cluster_id: {cluster_id}")
        ret, cluster = ClusterClient().read_cluster(cluster_id)
        if not ret:
            logger.error(f"Unable to query cluster data: {cluster}")
            raise Exception(f"unable to query cluster data, {cluster}")

        self.cluster = cluster
        logger.info("Cluster data loaded successfully")

        self.policy = self.load_policy()
        if self.policy:
            logger.info("Policy loaded successfully")
        else:
            logger.info("No policy found or policy not enabled")

    def load_policy(self):
        logger.debug("Loading policy from cluster config")
        try:
            config = self.cluster['config']

            stability_checker = config.get('stabilityChecker', None)
            if not stability_checker:
                logger.warning("No stabilityChecker section in config")
                return None

            stability_checker_policy_rule_uri = stability_checker.get(
                'policyRuleURI', '')
            if stability_checker_policy_rule_uri == "":
                logger.warning("policyRuleURI is empty")
                return None

            logger.info(
                f"Loading policy rule from URI: {stability_checker_policy_rule_uri}")
            policy_rule = LocalPolicyEvaluator(
                stability_checker_policy_rule_uri)
            return policy_rule

        except Exception as e:
            logger.exception("Exception occurred while loading policy")
            raise e

    def evaluate(self, input_data: dict):
        logger.info("Evaluating policy with provided input data")
        try:
            if not self.policy:
                logger.error("Policy rule for stability check not enabled")
                raise Exception("policy rule for stability check not enabled")

            ret_data = self.policy.execute_policy_rule({
                "cluster": self.cluster,
                "nodes_data": input_data
            })
            logger.info("Policy evaluation completed successfully")
            return ret_data

        except Exception as e:
            logger.exception("Exception occurred during policy evaluation")
            raise e


class ClusterStabilityChecker:
    def __init__(self):
        self.interval = int(
            os.getenv("CLUSTER_STABILITY_CHECK_INTERVAL", "60"))
        self.nodes_client = NodesAPIClient()
        self.executor = ClusterStabilityCheckerPolicyExecutor()
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        logger.info("Starting ClusterStabilityChecker loop")
        self.thread.start()

    def stop(self):
        logger.info("Stopping ClusterStabilityChecker loop")
        self._stop_event.set()
        self.thread.join()

    def _run(self):
        while not self._stop_event.is_set():
            try:
                logger.info("Fetching nodes status...")
                nodes_status = self.nodes_client.get_nodes_status()
                logger.debug(f"Fetched nodes status: {nodes_status}")

                logger.info("Evaluating cluster stability policy...")
                self.executor.evaluate(nodes_status)
            except Exception as e:
                logger.exception(f"Error during stability check: {e}")

            logger.debug(f"Sleeping for {self.interval} seconds...")
            time.sleep(self.interval)
