from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TemplateObject:
    templateUri: str = ''
    templatePolicyRuleUri: str = ''
    templateMetadata: Dict[str, str] = field(default_factory=dict)
    templateName: str = ''
    templateDescription: str = ''
    templateVersion: Dict[str, str] = field(
        default_factory=lambda: {"templateVersion": "", "tag": ""})
    templateTags: List[str] = field(default_factory=list)
    templateData: str = ''

    @classmethod
    def from_dict(cls, data: Dict) -> "TemplateObject":

        template_name = data.get("templateName", "")
        template_version = data.get(
            "templateVersion", {}).get("templateVersion", "")
        template_tag = data.get("templateVersion", {}).get("tag", "")

        inferred_template_uri = f"{template_name}:{template_version}-{template_tag}" if template_name and template_version and template_tag else ""

        return cls(
            templateUri=inferred_template_uri,
            templatePolicyRuleUri=data.get("templatePolicyRuleUri"),
            templateMetadata=data.get("templateMetadata", {}),
            templateName=template_name,
            templateDescription=data.get("templateDescription"),
            templateVersion=data.get(
                "templateVersion", {"templateVersion": "", "tag": ""}),
            templateTags=data.get("templateTags", []),
            templateData=data.get("templateData"),
        )

    def to_dict(self) -> Dict:

        return {
            "templateUri": self.templateUri,
            "templatePolicyRuleUri": self.templatePolicyRuleUri,
            "templateMetadata": self.templateMetadata,
            "templateName": self.templateName,
            "templateDescription": self.templateDescription,
            "templateVersion": self.templateVersion,
            "templateTags": self.templateTags,
            "templateData": self.templateData,
        }
