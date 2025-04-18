from .policy_sandbox import LocalPolicyEvaluator
from .schema import TemplateObject
from .crud import TemplateStoreDatabase
import logging

logger = logging.getLogger(__name__)


class TemplateExecutor:

    def __init__(self, template: TemplateObject) -> None:
        self.template = template
        self.policy_rule_uri = template.templatePolicyRuleUri

    def evaluate(self, input_data: dict, parameters: dict):
        try:

            policy_executor = LocalPolicyEvaluator(
                self.policy_rule_uri, parameters=parameters)
            converted_data = policy_executor.execute_policy_rule({
                "template_data": self.template.to_dict(),
                "spec": input_data
            })

            return converted_data

        except Exception as e:
            raise e


def execute_convertor_policy(template_db: TemplateStoreDatabase, input_data: dict, template_uri: str, parameters: dict):

    try:
        success, template = template_db.get_by_templateUri(template_uri)

        if not success:
            raise ValueError(f"Template with URI '{template_uri}' not found.")

        template_executor = TemplateExecutor(template)
        return template_executor.evaluate(input_data, parameters)

    except Exception as e:
        logger.error(f"Error in execute_convertor_policy: {e}")
        raise e
