import os
import logging

from .metrics import BlockMetricsClient, ClusterMetricsClient
from .cluster import ClusterClient
from .blocks import BlocksClient
from .metrics import get_block_metrics_collector
from .policy_sandbox import LocalPolicyEvaluator

from .k8s import join_node, remove_node

logger = logging.getLogger(__name__)


class ClusterMembership:
    def __init__(self) -> None:
        self.cluster_id = os.getenv("CLUSTER_ID")
        ret, cluster_data = ClusterClient().read_cluster(self.cluster_id)
        if not ret:
            logger.error("Failed to fetch cluster data")
            raise Exception("Cluster data not found")

        self.cluster_data = cluster_data
        self.is_initialized = False

        config = self.cluster_data.get('config', {})
        actions = config.get('actionsPolicyMap', {})
        action_policy = actions.get('add_node')

        if not action_policy or not action_policy.get('policyRuleURI'):
            logger.warning("No add_node policy found, skipping initialization")
            return

        policy_rule_uri = action_policy['policyRuleURI']
        parameters = action_policy.get('parameters', {})

        self.policy_evaluator = LocalPolicyEvaluator(
            policy_rule_uri, parameters)
        self.is_initialized = True
        logger.info("ClusterMembership policy evaluator initialized")

    def _get_metrics_base_uri(self) -> str:
        return os.getenv("CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000")

    def execute_pre_check(self, node_data: dict):
        if not self.is_initialized:
            logger.info("Policy not initialized, allowing node by default")
            return True, node_data

        try:
            base_uri = self._get_metrics_base_uri()
            cluster_metrics = ClusterMetricsClient(
                base_uri).get_cluster_metrics()
            if not cluster_metrics:
                raise Exception("Failed to retrieve cluster metrics")

            payload = {
                "cluster_data": self.cluster_data,
                "cluster_metrics": cluster_metrics,
                "node_data": node_data
            }

            response = self.policy_evaluator.execute_policy_rule(payload)
            allowed = response.get('allowed', False)
            updated_node_data = response.get('input_data', node_data)

            logger.info(f"Add node policy evaluated. Allowed: {allowed}")
            return allowed, updated_node_data

        except Exception as e:
            logger.exception("Error executing pre-check for node addition")
            raise

    def execute_mgmt_command(self, mgmt_action, mgmt_data):
        if not self.is_initialized:
            raise Exception("Add node policy is not initialized")

        try:
            return self.policy_evaluator.execute_mgmt_command(mgmt_action, mgmt_data)
        except Exception as e:
            logger.exception("Error executing add_node mgmt command")
            raise
    
    def join_node_to_cluster(self, node_data, mode: str = "local_network", custom_ip=None):
        try:

            allowed, node_data_modified = self.execute_pre_check(node_data)
            if not allowed:
                raise Exception(str(node_data_modified))

            data = join_node(node_data, node_data_modified['id'], mode, custom_ip)
            return data
    
        except Exception as e:
            raise e


class ClusterDeMembership:
    def __init__(self) -> None:
        self.cluster_id = os.getenv("CLUSTER_ID")
        ret, cluster_data = ClusterClient().read_cluster(self.cluster_id)
        if not ret:
            logger.error("Failed to fetch cluster data")
            raise Exception("Cluster data not found")

        self.cluster_data = cluster_data
        self.is_initialized = False
        self.blocks_client = BlocksClient()

        config = self.cluster_data.get('config', {})
        actions = config.get('actionsPolicyMap', {})
        action_policy = actions.get('remove_node')

        if not action_policy or not action_policy.get('policyRuleURI'):
            logger.warning(
                "No remove_node policy found, skipping initialization")
            return

        policy_rule_uri = action_policy['policyRuleURI']
        parameters = action_policy.get('parameters', {})

        settings = {
            "get_block_by_id": self.blocks_client.get_block_by_id,
            "query_blocks": self.blocks_client.query_blocks
        }

        self.policy_evaluator = LocalPolicyEvaluator(
            policy_rule_uri, parameters, settings)
        self.is_initialized = True
        logger.info("ClusterDeMembership policy evaluator initialized")

    def _get_metrics_base_uri(self) -> str:
        return os.getenv("CLUSTER_METRICS_SERVICE_URL", "http://localhost:5000")

    def execute_pre_check(self, node_id: str):
        if not self.is_initialized:
            logger.info(
                "Policy not initialized, allowing node removal by default")
            return True, node_id

        try:
            base_uri = self._get_metrics_base_uri()
            cluster_metrics = ClusterMetricsClient(base_uri).get_cluster_metrics()
            if not cluster_metrics:
                raise Exception("Failed to retrieve cluster metrics")

            blocks = BlockMetricsClient(base_uri).query_documents({
                "nodeId": node_id
            })

            payload = {
                "cluster_data": self.cluster_data,
                "cluster_metrics": cluster_metrics,
                "node_id": node_id,
                "block_instances": blocks
            }

            response = self.policy_evaluator.execute_policy_rule(payload)
            allowed = response.get('allowed', False)
            updated_node_id = response.get('input_data', node_id)

            logger.info(f"Remove node policy evaluated. Allowed: {allowed}")
            return allowed, updated_node_id

        except Exception as e:
            logger.exception("Error executing pre-check for node removal")
            raise

    def execute_mgmt_command(self, mgmt_action, mgmt_data):
        if not self.is_initialized:
            raise Exception("Remove node policy is not initialized")

        try:
            return self.policy_evaluator.execute_mgmt_command(mgmt_action, mgmt_data)
        except Exception as e:
            logger.exception("Error executing remove_node mgmt command")
            raise
    
    def remove_node_from_cluster(self, node_id):
        try:

            allowed, node_id_modified = self.execute_pre_check(node_id)
            if not allowed:
                raise Exception(str(node_id_modified))

            data = remove_node(node_id_modified)
            return data
    
        except Exception as e:
            raise e
