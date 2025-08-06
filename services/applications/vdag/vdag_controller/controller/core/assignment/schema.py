from dataclasses import dataclass, field
from typing import List, Dict, Any


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
