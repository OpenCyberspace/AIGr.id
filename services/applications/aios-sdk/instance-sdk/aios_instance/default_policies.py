import logging

logging.basicConfig(level=logging.DEBUG)
logging = logging.getLogger(__name__)


class DefaultPreprocessingPolicy:

    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters
        logging.info("[Policy rule] Default pre-processing policy executed")

    def eval(self, parameters, input_data, context):

        try:
            return input_data
        except Exception as e:
            raise e


class DefaultPostprocessingPolicy:

    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters
        logging.info("[Policy rule] Default post-processing policy executed")

    def eval(self, parameters, input_data, context):

        try:
            return input_data
        except Exception as e:
            raise e

