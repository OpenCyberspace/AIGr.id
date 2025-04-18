from dataclasses import dataclass, field
from typing import List, Dict, Any
import requests
import os

from .policy_sandbox import LocalPolicyEvaluator


@dataclass
class NodeObject:
    nodeLabel: str = ''
    nodeType: str = ''
    vdagURI: str = ''
    assignmentPolicyRule: Dict[str, Any] = field(default_factory=dict)
    preprocessingPolicyRule: Dict[str, Any] = field(default_factory=dict)
    postprocessingPolicyRule: Dict[str, Any] = field(default_factory=dict)
    modelParameters: Dict[str, Any] = field(default_factory=dict)
    outputProtocol: Dict[str, Any] = field(default_factory=dict)
    inputProtocol: Dict[str, Any] = field(default_factory=dict)
    IOMap: List[Dict[str, Any]] = field(default_factory=list)
    manualBlockId: str = field(default_factory=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeObject':
        return cls(
            nodeLabel=data.get('nodeLabel', ''),
            nodeType=data.get('nodeType', ''),
            assignmentPolicyRule=data.get('assignmentPolicyRule', {}),
            preprocessingPolicyRule=data.get('preprocessingPolicyRule', {}),
            postprocessingPolicyRule=data.get('postprocessingPolicyRule', {}),
            modelParameters=data.get('modelParameters', {}),
            outputProtocol=data.get('outputProtocol', {}),
            inputProtocol=data.get('inputProtocol', {}),
            IOMap=data.get('IOMap', []),
            vdagURI=data.get('vdagURI', ''),
            manualBlockId=data.get('manualBlockId', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'nodeLabel': self.nodeLabel,
            'nodeType': self.nodeType,
            'assignmentPolicyRule': self.assignmentPolicyRule,
            'preprocessingPolicyRule': self.preprocessingPolicyRule,
            'postprocessingPolicyRule': self.postprocessingPolicyRule,
            'modelParameters': self.modelParameters,
            'outputProtocol': self.outputProtocol,
            'inputProtocol': self.inputProtocol,
            'IOMap': self.IOMap,
            'vdagURI': self.vdagURI,
            'manualBlockId': self.manualBlockId
        }


@dataclass
class vDAGObject:
    vdag_name: str = ''
    vdag_version: Dict[str, str] = field(
        default_factory=lambda: {'version': '', 'release-tag': ''})
    vdagURI: str = ''
    discoveryTags: List[str] = field(default_factory=list)
    controller: Dict[str, Any] = field(default_factory=lambda: {
        'inputSources': [],
        'initParameters': {},
        'initSettings': {},
        'policies': []
    })
    nodes: List[NodeObject] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict)
    assignment_info: Dict = field(default_factory=dict)
    status: str = field(default="pending")
    compiled_graph_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'vDAGObject':
        vdag_name = data.get('vdag_name', '')
        vdag_version = data.get(
            'vdag_version', {'version': '', 'release-tag': ''})
        vdagURI = f"{vdag_name}:{vdag_version.get('version', '')}-{vdag_version.get('release-tag', '')}" if vdag_name and vdag_version.get(
            'version') and vdag_version.get('release-tag') else ''
        discovery_tags = data.get('discoveryTags', [])
        controller = data.get('controller', {
            'inputSources': [],
            'initParameters': {},
            'initSettings': {},
            'policies': []
        })
        nodes_data = data.get('nodes', [])
        nodes = [NodeObject.from_dict(node) for node in nodes_data]
        graph = data.get('graph', {})
        status = data.get('status', 'pending')
        assignment_info = data.get('assignment_info', {})
        compiled_graph_data = data.get('compiled_graph_data', {})

        return cls(
            vdag_name=vdag_name,
            vdag_version=vdag_version,
            vdagURI=vdagURI,
            discoveryTags=discovery_tags,
            controller=controller,
            nodes=nodes,
            graph=graph,
            status=status,
            assignment_info=assignment_info,
            compiled_graph_data=compiled_graph_data
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'vdag_name': self.vdag_name,
            'vdag_version': self.vdag_version,
            'vdagURI': self.vdagURI,
            'discoveryTags': self.discoveryTags,
            'controller': self.controller,
            'nodes': [node.to_dict() for node in self.nodes],
            'graph': self.graph,
            'assignment_info': self.assignment_info,
            'status': self.status,
            'compiled_graph_data': self.compiled_graph_data
        }


class vDAGDBClient:
    def __init__(self):
        self.base_url = os.getenv("VDAG_DB_API_URL", "http://localhost:10501")

    def get_vdag(self, vdagURI: str):
        try:
            response = requests.get(f"{self.base_url}/vdag/{vdagURI}")
            response.raise_for_status()
            data = response.json()["data"]
            return vDAGObject.from_dict(data)
        except requests.RequestException as e:
            raise e


class vDAGPreprocessor:

    def __init__(self, block_id: str) -> None:
        self.vdag_db = vDAGDBClient()
        self.policies_cache: Dict[str, LocalPolicyEvaluator] = {}
        self.block_id = block_id

    def get_preprocessor(self, vdag_uri):
        try:
            if vdag_uri not in self.policies_cache:

                # add a new policy:
                vdag = self.vdag_db.get_vdag(vdag_uri)
                rev_mapping = vdag.compiled_graph_data['rev_mapping']

                node_label = rev_mapping.get(self.block_id)
                if not node_label:
                    return None

                policy = None

                # get the node with the given label:
                for node in vdag.nodes:
                    if node.nodeLabel == node_label:
                        policy = node.preprocessingPolicyRule
                        break
                else:
                    return None

                if policy is None or len(policy) == 0:
                    return None

                policy_rule_uri = policy.get('policyRuleURI', None)
                if policy_rule_uri is None:
                    raise Exception("policy rule not specified")

                parameters = policy.get('parameters', {})

                # load the policy rule
                local_policy = LocalPolicyEvaluator(
                    policy_rule_uri, parameters=parameters)
                self.policies_cache[vdag_uri] = local_policy
            else:
                return self.policies_cache[vdag_uri]

        except Exception as e:
            raise e

    def execute_policy_rule_if_present(self, session_id: str, packet):
        try:

            splits = session_id.split(":::")
            if len(splits) != 3:
                raise Exception("malformed packet session_id")

            vdag_uri = splits[1]

            policy_rule = self.get_preprocessor(vdag_uri)
            if not policy_rule:
                return packet

            response = policy_rule.execute_policy_rule({
                "packet": packet
            })

            return response['packet']

        except Exception as e:
            raise e
