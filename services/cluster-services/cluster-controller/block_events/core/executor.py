from .blocks import BlocksClient

from .policy_sandbox import LocalPolicyEvaluator


class BlockEventExecutor:

    def __init__(self, block_id, event_name):
        self.block_id = block_id
        self.block_client = BlocksClient()
        self.block_data = self.get_block_data()

        self.policy = self.setup_policy(event_name)

    def get_block_data(self):
        try:
            data = self.block_client.get_block_by_id(self.block_id)
            if 'error' in data:
                raise Exception("Failed to obtain block data")

            return data

        except Exception as e:
            raise e

    def setup_policy(self, event_name):
        try:
            block_init_data = self.block_data['blockInitData']
            events_map = block_init_data['events'].get({})

            if event_name not in events_map:
                raise Exception("event not registered")

            events_policy_rule_uri = events_map[event_name]

            if events_policy_rule_uri == "":
                raise Exception("block has not specified policy rule URI")

            policy = LocalPolicyEvaluator(events_policy_rule_uri)
            return policy
        except Exception as e:
            raise e

    def execute_event(self, event_name, event_data):
        try:
            if not self.policy:
                raise Exception("policy not loaded")

            result = self.policy.execute_policy_rule({
                "block_id": self.block_id,
                "event_name": event_name,
                "event_data": event_data
            })

            return result

        except Exception as e:
            raise e


class ExecutorsCache:
    def __init__(self):
        self.executors_map = {}

    def get_or_create_executor(self, block_id, event_name):

        key = f"{block_id}__{event_name}"

        if key not in self.executors_map:
            self.executors_map[key] = BlockEventExecutor(block_id, event_name=event_name)
        return self.executors_map[key]

    def execute_event(self, block_id, event_name, event_data):
        executor = self.get_or_create_executor(block_id, event_name)
        return executor.execute_event(event_name, event_data)