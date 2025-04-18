

class DefaultAutoscalerPolicy:

    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

        print(self.settings["get_metrics"]())

    def eval(self, parameters, input_data, context):

        try:

            print(self.settings["get_metrics"]())

            return {
                "skip": False,
                "operation": "scale"
            }

        except Exception as e:
            raise e
