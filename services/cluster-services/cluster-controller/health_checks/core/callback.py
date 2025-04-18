import logging
from .policy_sandbox import LocalPolicyEvaluator
from .default_policy import DefaultClusterResourceAllocatorPolicy

logging.basicConfig(level=logging.INFO)


class PolicyEvaluator:

    def __init__(self, policy_rule_uri: str, settings: str, block_id: str):
        self.policy_rule_uri = policy_rule_uri
        self.settings = settings

        self.policy = LocalPolicyEvaluator("", settings=settings, parameters={}, custom_class=DefaultClusterResourceAllocatorPolicy)
        self.policy.settings = settings
        self.block_id = block_id

    def execute_rule(self, instance_id):
        try:

            self.policy.execute_policy_rule(
                {"instance_id": instance_id, "block_id": self.block_id}
            )

        except Exception as e:
            return False, str(e)
    
    def mgmt(self, action, data):
        return self.policy.execute_mgmt_command(action, data)
