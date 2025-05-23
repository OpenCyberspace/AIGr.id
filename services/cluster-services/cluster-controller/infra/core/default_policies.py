

class DefaultClusterResourceAllocatorPolicy:

    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

    def eval(self, parameters, input_data, context):

        try:

            if input_data['action'] == 'dry_run':
                return {
                    "selection_score_data": {
                        "score": 0.9,
                        "node_info": {
                            
                        }
                    }
                }

            if input_data['action'] == 'allocation':
                return {
                    "node_id": "",
                    "gpus": []
                }

            else:
                raise Exception(
                    f"action {input_data['action']} not implemented")

        except Exception as e:
            raise e
