from .policy_sandbox import PolicyFunctionExecutor
from .pusher import OutputPusher
import os
import json


class JobInit:

    def __init__(self) -> None:
        self.pusher = OutputPusher(
            redis_host=os.getenv("JOB_OUTPUT_REDIS_HOST", "localhost"),
            redis_queue=os.getenv("DB_API_URL", "JOB_OUTPUTS")
        )

        self.policy_function = PolicyFunctionExecutor(
            policy_rule_uri=os.getenv("POLICY_RULE_URI"),
            parameters=json.loads(os.getenv("POLICY_RULE_PARAMETERS", "{}")),
            settings=None,
            custom_class=None
        )

        self.job_id = os.getenv("JOB_ID", "")

        self.inputs = json.loads(os.getenv("POLICY_INPUTS", "{}"))

    def execute(self):
        try:
            output = self.policy_function.execute(self.inputs)
            self.pusher.push(self.job_id, output, "completed",
                             "", os.getenv("POLICY_RULE_URI"))
        except Exception as e:
            self.pusher.push(self.job_id, {"message": str(
                e)}, "failed", "", os.getenv("POLICY_RULE_URI"))
