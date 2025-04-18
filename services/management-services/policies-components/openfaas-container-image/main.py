import requests
import json

from policy_sandbox import LocalPolicyEvaluator
from webhooks import component_registry, dag_runtime_db, hardware_registry, metrics
from webhooks.policydb import policies


class PolicyExecutor:

    def __init__(self, task_json) -> None:
        self.task_json = task_json

        self.webhooks = {
            "policy_db": policies.PoliciesDB,
            "component_registry": component_registry.ComponentRegistry,
            "dag_runtime_db": dag_runtime_db.DB_API,
            "hardware_registry": hardware_registry.HardwareRegistryAPI,
            "metrics_blocks": metrics.BlockMetricsCollectorAPI,
            "metrics_hardware": metrics.HardwareMetricsCollectorAPI
        }

        # load cluster resource allocation policy rule
        self.policy_rule = LocalPolicyEvaluator(
            task_json['policy_rule_id'])
        
        self.policy_rule.settings['webhooks'] = self.webhooks

        self.inputs = task_json['inputs']

    def execute_task(self):

        try:

            ret, results = self.policy_rule.execute_policy_rule(
                self.inputs)

            if not ret:
                raise Exception(results)

            return results

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


def handle(req):

    task_json = json.loads(req)
    executor = PolicyExecutor(task_json)

    result = executor.execute_task()
    return json.dumps(result)
