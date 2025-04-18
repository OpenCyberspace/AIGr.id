from ..policy_sandbox import LocalPolicyEvaluator
from ..webhooks.blocks import BlocksClient
from ..webhooks.clusters import ClusterClient
from .policy_executor_api import PolicyRemoteExecutor

import os


class ShareabilityChecker:

    def __init__(self, ir: dict, mode: str) -> None:
        self.ir = ir
        self.ranking_policy_rule = ir['rankingPolicyRule']
        self.mode = mode

    def execute(self, target_block_id: str, full_vdag_data, vdag_node_data: str):
        try:

            block_data = BlocksClient().get_block_by_id(target_block_id)

            if 'error' in block_data:
                raise Exception(block_data['error'])

            ret, cluster_data = ClusterClient().read_cluster(
                block_data['cluster_id']
            )

            if not ret:
                raise Exception(str(cluster_data))

            if self.mode != "remote":

                self.policy_rule = LocalPolicyEvaluator(
                    self.ranking_policy_rule['policyRuleURI'],
                    self.ranking_policy_rule['settings'],
                    self.ranking_policy_rule['parameters']
                )

                self.filter = self.policy_rule.parameters.get('filter', None)

                result = self.policy_rule.execute_policy_rule({
                    "block": block_data,
                    "cluster": cluster_data,
                    "node": vdag_node_data,
                    "vdag": full_vdag_data
                })

                return result
            else:

                policy_executor_uri = os.getenv("POLICY_REMOTE_URL")

                executor = PolicyRemoteExecutor(policy_executor_uri, self.ranking_policy_rule['policyRuleURI'], {
                    "block": block_data,
                    "cluster": cluster_data,
                    "node": vdag_node_data,
                    "vdag": full_vdag_data
                }, self.ranking_policy_rule['parameters']
                )

                response = executor.execute()
                if "success" in response and response["success"]:
                    return response["policy_rule_output"]
                else:
                    raise Exception(response["message"])

        except Exception as e:
            raise e
