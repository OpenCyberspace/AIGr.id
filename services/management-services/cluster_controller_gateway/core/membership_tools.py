import os
import logging
import json

from .global_metrics import GlobalBlocksMetricsClient, GlobalClusterMetricsClient
from .cluster_db import ClusterClient
from .blocks import BlocksClient
from .policy_sandbox import LocalPolicyEvaluator

logger = logging.getLogger(__name__)


class BaseClusterPolicy:
    def __init__(self, cluster_id: str, action_type: str):
        self.cluster_id = cluster_id
        self.cluster_data = self._load_cluster_data(cluster_id)
        self.policy_evaluator = None
        self.is_initialized = False

        try:
            actions = json.loads(
                os.getenv("CLUSTER_CONTROLLER_GATEWAY_ACTIONS_MAP", '{}'))
        except json.JSONDecodeError:
            logger.exception(
                "Failed to parse CLUSTER_CONTROLLER_GATEWAY_ACTIONS_MAP")
            actions = {}

        action_policy = actions.get(action_type)
        if not action_policy or not action_policy.get('policyRuleURI'):
            logger.warning(
                f"No '{action_type}' policy found, skipping initialization")
            return

        policy_rule_uri = action_policy['policyRuleURI']
        parameters = action_policy.get('parameters', {})

        settings = self.get_settings_for_policy()
        self.policy_evaluator = LocalPolicyEvaluator(
            policy_rule_uri, parameters, settings)
        self.is_initialized = True
        logger.info(f"{self.__class__.__name__} policy evaluator initialized")

    def _load_cluster_data(self, cluster_id):
        ret, cluster_data = ClusterClient().read_cluster(cluster_id)
        if not ret:
            logger.error("Failed to fetch cluster data")
            raise Exception("Cluster data not found")
        return cluster_data

    def get_settings_for_policy(self):
        return None

    def execute_mgmt_command(self, mgmt_action, mgmt_data):
        if not self.is_initialized:
            raise Exception(
                f"{self.__class__.__name__} policy is not initialized")

        try:
            return self.policy_evaluator.execute_mgmt_command(mgmt_action, mgmt_data)
        except Exception as e:
            logger.exception(
                f"Error executing {self.__class__.__name__} mgmt command")
            raise


class ClusterMembership(BaseClusterPolicy):
    def __init__(self, cluster_id) -> None:
        super().__init__(cluster_id, action_type="add_node")

    def execute_pre_check(self, node_data: dict):
        if not self.is_initialized:
            logger.info(
                "Add node policy not initialized, allowing node by default")
            return True, node_data

        try:
            cluster_metrics = GlobalClusterMetricsClient().get_cluster(self.cluster_id)
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


class ClusterDeMembership(BaseClusterPolicy):
    def __init__(self, cluster_id: str) -> None:
        self.blocks_client = BlocksClient()
        super().__init__(cluster_id, action_type="remove_node")

    def get_settings_for_policy(self):
        return {
            "get_block_by_id": self.blocks_client.get_block_by_id,
            "query_blocks": self.blocks_client.query_blocks
        }

    def execute_pre_check(self, node_id: str):
        if not self.is_initialized:
            logger.info(
                "Remove node policy not initialized, allowing removal by default")
            return True, node_id

        try:
            cluster_metrics = GlobalClusterMetricsClient().get_cluster(self.cluster_id)
            if not cluster_metrics:
                raise Exception("Failed to retrieve cluster metrics")

            blocks = GlobalBlocksMetricsClient(
                "").query_blocks({"clusterId": self.cluster_id})

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
