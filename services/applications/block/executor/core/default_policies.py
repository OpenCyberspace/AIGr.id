

class LoadBalancerPolicyRule:

    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

        # print(self.settings["get_metrics"]())

    def eval(self, parameters, input_data, context):

        try:

            # print(self.settings["metrics"]())

            return {
                "instance_id": "1"
            }

        except Exception as e:
            raise e
