from re import L
from threading import local
from typing import Dict
from .state import StateManager, InMemoryDefaultStateBackend
from .loader import load_module_from_local_path, load_policy_rule_from_db, ModuleLoadException
from uuid import uuid4
from copy import deepcopy
from .utils import V1PolicyRuleParser


REQUIRED_METHODS = [
    "eval",
    "on_parameter_update",
    "flush",
    "get_initial_params"
]

VALIDATORS = {
    "Policy/v1": V1PolicyRuleParser
}

class LocalPolicyEvaluator:

    # load code from policy rule id
    def __init__(self, policy_rule_id: str) -> None:
        self.policy_rule_id = policy_rule_id
        self.settings = {}
        self.parameters = {}

        self.id = policy_rule_id

        policy_url, settings, parameters = load_policy_rule_from_db(self.id)

        self.settings = settings
        self.parameters = parameters

        self.load_from_path(policy_url, self.settings, self.parameters, None)

    # load code from policy rule path - can be an URL or local fs path
    def load_from_path(self, policy_rule_path: str, settings: dict, parameters: dict, cache_backend) -> None:

        self.settings = self.settings
        self.parameters = parameters

        self.backend = cache_backend if cache_backend is not None else InMemoryDefaultStateBackend()

        self.state = StateManager({}, self.backend)
        self.id = str(uuid4())

        # load from path
        policy_rule_class = load_module_from_local_path(self.id, policy_rule_path)
        self.policy_rule_instance = policy_rule_class(self.id, deepcopy(self.settings), deepcopy(self.parameters))

        # check methods 
        for required_method in REQUIRED_METHODS:
            if not hasattr(self.policy_rule_instance, required_method):
                raise ModuleLoadException('provided policy rule has no method ' + required_method)

    
    def execute_policy_rule(self, inputs: dict):
        return self.policy_rule_instance.eval(self.parameters, inputs, self.state)

    def update_parameter(self, parameter: dict, value):
        self.parameters[parameter] = value
    
    def flush(self):
        self.state.flush()
        self.policy_rule_instance.flush()


class RuleExistException(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(name)
    
    def __str__(self) -> str:
        return "rule with name {} already exist".format()

class RuleNotFoundException(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(name)
    
    def __str__(self) -> str:
        return "rule with name {} not found".format()


class PolicyRulesManager:
    def __init__(self) -> None:
        self.loaded_rules: Dict[str, LocalPolicyEvaluator] = {}
    
    def register_rule_by_id(self, local_name: str, id: str):
        if local_name in self.loaded_rules:
            raise RuleExistException(local_name)
        self.loaded_rules[local_name] = LocalPolicyEvaluator(id)
    
    def register_rule_from_path(self, local_name: str, path: str, settings: dict, parameters: dict, cache_backend = None, schema=None):
        if local_name in self.loaded_rules:
            raise RuleExistException(local_name)
        self.loaded_rules[local_name] = LocalPolicyEvaluator(path, settings, parameters, cache_backend = None)
    
    def remove_rule(self, local_name: str):
        if local_name not in self.loaded_rules:
            raise RuleNotFoundException(local_name)
        self.loaded_rules[local_name].flush()
        del self.loaded_rules[local_name]
    
    def execucte_policy_rule(self, local_name, parameters: dict):
        if local_name not in self.loaded_rules:
            raise RuleNotFoundException(local_name)
        return self.loaded_rules[local_name].execute_policy_rule(parameters)
    
    def flush_all(self):
        for local_name in self.loaded_rules:
            self.remove_rule(local_name)
    
    def update_parameter(self, local_name: str, parameter_name: str, value):
        if local_name not in self.loaded_rules:
            raise RuleNotFoundException(local_name)
        self.loaded_rules[local_name].update_parameter(parameter_name, value)
    
