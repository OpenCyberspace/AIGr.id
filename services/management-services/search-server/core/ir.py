import json
import logging


def search_IR(json_doc):
    try:
        search_data = json_doc['body']['values']

        logging.info("Parsing matchType field")
        match_type = search_data.get('matchType')

        logging.info("Parsing rankingPolicyRule field")
        ranking_policy_rule = search_data.get(
            'rankingPolicyRule', {}).get('values', {})

        logging.info("Parsing executionMode field")
        execution_mode = ranking_policy_rule.get('executionMode')

        logging.info("Parsing policyRuleURI field")
        policy_rule_uri = ranking_policy_rule.get('policyRuleURI')

        logging.info("Parsing settings field")
        settings = ranking_policy_rule.get('settings', {})

        logging.info("Parsing parameters field")
        parameters = ranking_policy_rule.get('parameters', {})

        logging.info("Parsing filter field in parameters")

        similarity_search_dict = {
            "matchType": match_type,
            "rankingPolicyRule": {
                "executionMode": execution_mode,
                "policyRuleURI": policy_rule_uri,
                "policyCodePath": ranking_policy_rule.get('policyCodePath'),
                "settings": settings,
                "parameters": parameters
            }
        }

        return similarity_search_dict
    except KeyError as e:
        logging.error(f"Missing key in JSON document: {e}")
        raise e
    except Exception as e:
        logging.error(f"Error parsing JSON document: {e}")
        raise e


type_action_dispatcher = {
    "search": search_IR
}


def ir(spec: dict):
    try:
        action_function = type_action_dispatcher["search"]
        return action_function(spec)

    except Exception as e:
        raise e
