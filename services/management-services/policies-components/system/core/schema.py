from dataclasses import dataclass, field, asdict
from typing import Dict, List


@dataclass
class PolicyRule:
    policy_rule_uri: str
    name: str
    version: str
    release_tag: str
    metadata: Dict
    tags: str
    code: str
    code_type: str
    type: str
    policy_input_schema: Dict
    policy_output_schema: Dict
    policy_settings_schema: Dict
    policy_parameters_schema: Dict
    policy_settings: Dict
    policy_parameters: Dict
    description: str
    functionality_data: Dict
    resource_estimates: Dict

    @staticmethod
    def from_dict(data: Dict) -> 'PolicyRule':
        return PolicyRule(
            policy_rule_uri=f"{data['name']}:{data['version']}-{data['release_tag']}",
            name=data['name'],
            version=data['version'],
            release_tag=data['release_tag'],
            metadata=data['metadata'],
            tags=data['tags'],
            code=data['code'],
            code_type=data['code_type'],
            type=data['type'],
            policy_input_schema=data['policy_input_schema'],
            policy_output_schema=data['policy_output_schema'],
            policy_settings_schema=data['policy_settings_schema'],
            policy_parameters_schema=data['policy_parameters_schema'],
            policy_settings=data['policy_settings'],
            policy_parameters=data['policy_parameters'],
            description=data['description'],
            functionality_data=data['functionality_data'],
            resource_estimates=data['resource_estimates']
        )

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PolicyExecutors:
    executor_id: str
    executor_host_uri: str
    executor_metadata: Dict
    executor_hardware_info: Dict
    executor_status: str = field(default="healthy")

    @staticmethod
    def from_dict(data: Dict) -> 'PolicyExecutors':
        return PolicyExecutors(
            executor_id=data['executor_id'],
            executor_host_uri=data['executor_host_uri'],
            executor_metadata=data['executor_metadata'],
            executor_hardware_info=data['executor_hardware_info'],
            executor_status=data.get('executor_status', "healthy"),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Function:
    function_id: str
    function_executor_id: str
    function_executor_uri: str
    function_metadata: Dict
    function_tags: List[str]
    function_policy_rule_uri: str
    function_policy_data: Dict

    @staticmethod
    def from_dict(data: Dict) -> 'Function':
        return Function(
            function_id=data['function_id'],
            function_executor_id=data['function_executor_id'],
            function_executor_uri=data['function_executor_uri'],
            function_metadata=data['function_metadata'],
            function_tags=data['function_tags'],
            function_policy_rule_uri=data['function_policy_rule_uri'],
            function_policy_data=data['function_policy_data'],
        )

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Graph:
    graph_uri: str
    graph_name: str
    graph_version: str
    graph_release_tag: str
    graph_metadata: str
    graph_function_ids: List[str]
    graph_connection_data: Dict
    graph_search_tags: List[str]
    graph_description: str
    graph_input_schema: Dict
    graph_output_schema: Dict

    @staticmethod
    def from_dict(data: Dict) -> 'Graph':
        graph_name = data['graph_name']
        graph_version = data['graph_version']
        graph_release_tag = data['graph_release_tag']
        graph_uri = f"{graph_name}:{graph_version}-{graph_release_tag}"
        return Graph(
            graph_uri=graph_uri,
            graph_name=graph_name,
            graph_version=graph_version,
            graph_release_tag=graph_release_tag,
            graph_metadata=data['graph_metadata'],
            graph_function_ids=data['graph_function_ids'],
            graph_connection_data=data['graph_connection_data'],
            graph_search_tags=data['graph_search_tags'],
            graph_description=data['graph_description'],
            graph_input_schema=data['graph_input_schema'],
            graph_output_schema=data['graph_output_schema']
        )

    def to_dict(self) -> Dict:
        return asdict(self)
