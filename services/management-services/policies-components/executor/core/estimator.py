from .stateful_executor import PolicyFunctionExecutor
from .db import PolicyRule
from .metrics import get_metrics_collector

import os


class ResourceEstimator:

    def __init__(self) -> None:

        self.policy_rule_uri = os.getenv("RESOURCE_ESTIMATOR_POLICY_RULE_URI")

        if not self.policy_rule_uri:
            self.policy_rule = None
            return

        self.metrics_collector = get_metrics_collector()
        settings = {
            "get_metrics": self.metrics_collector
        }

        self.policy_rule = PolicyFunctionExecutor(
            self.policy_rule_uri, parameters={}, settings=settings
        )

    def __estimate_internal(self, input_policy_rule: PolicyRule, type_):
        try:

            resource_estimates = input_policy_rule.resource_estimates
            if not resource_estimates:
                raise Exception(
                    "resource allocator policy not provided for the node")
            else:
                input_data = input_policy_rule.to_dict()
                result = self.policy_rule.execute_policy_rule({
                    "policy": input_data,
                    "type_": type_
                })
                return result

        except Exception as e:
            raise e

    def estimate(self, input_policy_rule: PolicyRule, type_="deployment"):
        try:
            result = self.__estimate_internal(input_policy_rule, type_)
            if 'allowed' not in result:
                raise Exception(
                    "invalid output data from estimator, key 'allowed' not found")

            if 'node_id' not in result:
                raise Exception(
                    "invalid output data from estimator, key 'node_id' not found")

            return result['allowed'], result['node_id']

        except Exception as e:
            raise e
