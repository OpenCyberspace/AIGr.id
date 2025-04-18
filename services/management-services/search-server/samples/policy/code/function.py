import requests

class AIOSv1PolicyRule:
    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

    def eval(self, parameters, input_data, context):
        return input_data
