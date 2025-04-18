

class ClusterSelectorPolicyRule:
   
    def __init__(self, rule_id, settings, parameters):

        self.rule_id = rule_id
        self.settings = settings
        self.parameters = parameters

    def eval(self, parameters, input_data, context):

        try:

            if input_data['action'] == "selection":

                print(parameters, input_data, context)

                filter_result = input_data['filter_result']
                if len(filter_result) == 0:
                    raise Exception("no results found in the filter")

                result = {}

                result['clusters'] = filter_result

                return result

            if input_data['action'] == "post_dry_run":

                selected_clusters = input_data['clusters']

                # sort the cluster having highest score:
                highest_index = 0
                current_highest = -1
                idx = 0

                for entry in selected_clusters:
                    score_data = entry["score_data"]
                    if score_data['score'] > current_highest:
                        current_highest = score_data['score']
                        highest_index = idx
                        idx += 1

                # selected cluster:
                return selected_clusters[highest_index]

        except Exception as e:
            raise e


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
                        "node": input_data['cluster']['nodes']['nodeData'][0]
                    }
                }
            
            else:
                raise Exception(f"action {input_data['action']} not implemented")

        except Exception as e:
            raise e