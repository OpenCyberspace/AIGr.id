import logging


class DefaultClusterResourceAllocatorPolicy:

    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

        self.count = 0

    def eval(self, parameters, input_data, context):

        try:

            self.count += 1
            if self.count > 5:
                logging.error(
                    f"block {input_data} not healthy after {self.count} times.")
                self.count = 0

        except Exception as e:
            raise e
