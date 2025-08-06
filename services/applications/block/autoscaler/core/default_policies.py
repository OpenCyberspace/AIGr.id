import logging

class DefaultAutoscalerPolicy:

    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

        print(self.settings["get_metrics"]())

    def eval(self, parameters, input_data, context):

        try:

            logging.info("input", input)
            metrics = self.settings["get_metrics"]()
            logging.info("got metrics: {}".format(metrics))

            return {
                "skip": True,
                "operation": ""
            }

        except Exception as e:
            raise e
