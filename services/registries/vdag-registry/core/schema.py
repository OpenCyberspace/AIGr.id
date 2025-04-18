from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class NodeObject:

    # a unique human readable label can be assigned to each node
    nodeLabel: str = ''

    # can be a unique type representing the type of the node, 
    # if nodeType="vdag" then the vdagURI is considered to be the sub-vDAG
    nodeType: str = ''

    # vDAG URI if the nodeType=vdag, in this case, points to another vDAG
    vdagURI: str = ''

    # policy used for assignment (finding a block) for this node of the vDAG, this will be taken into consideration when:
    # nodeType != "vdag" and manualBlockId is empty
    assignmentPolicyRule: Dict[str, Any] = field(default_factory=dict)

    # policy used by the block for this vDAG's session before sending the actual input to the instance for processing
    preprocessingPolicyRule: Dict[str, Any] = field(default_factory=dict)

    # policy used by the block for this vDAG's session after the instance produces an output
    postprocessingPolicyRule: Dict[str, Any] = field(default_factory=dict)

    # vDAG node specific parameters to be used by the instance, can be empty if defaults need to be used
    modelParameters: Dict[str, Any] = field(default_factory=dict)

    # Ignore
    outputProtocol: Dict[str, Any] = field(default_factory=dict)
    
    # Ignore
    inputProtocol: Dict[str, Any] = field(default_factory=dict)

    # Ignore
    IOMap: List[Dict[str, Any]] = field(default_factory=list)

    # manually assign a block to the vDAG's node, this can be 
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

    # name of the vDAG
    vdag_name: str = ''

    # version like 0.0.01, release tags like 'stable', 'beta' etc
    vdag_version: Dict[str, str] = field(
        default_factory=lambda: {'version': '', 'release-tag': ''})

    # vDAG URI is formed from version 
    vdagURI: str = ''

    # tags used for search and discovery
    discoveryTags: List[str] = field(default_factory=list)

    # controller configuration 
    controller: Dict[str, Any] = field(default_factory=dict)

    # list of nodes - points to the "NodeObject"
    nodes: List[NodeObject] = field(default_factory=list)

    # graph structure (explained in depth next)
    graph: Dict[str, Any] = field(default_factory=dict)

    # system generated (ignore)
    assignment_info: Dict = field(default_factory=dict)

    # system generated (ignore)
    status: str = field(default="pending")

    # system generated (ignore)
    compiled_graph_data: Dict[str, Any] = field(default_factory=dict)

    # metadata of the vDAG used for searching 
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'vDAGObject':
        vdag_name = data.get('vdag_name', '')
        vdag_version = data.get(
            'vdag_version', {'version': '', 'release-tag': ''})
        vdagURI = f"{vdag_name}:{vdag_version.get('version', '')}-{vdag_version.get('release-tag', '')}" if vdag_name and vdag_version.get(
            'version') and vdag_version.get('release-tag') else ''
        discovery_tags = data.get('discoveryTags', [])
        controller = data.get('controller', {})
        nodes_data = data.get('nodes', [])
        nodes = [NodeObject.from_dict(node) for node in nodes_data]
        graph = data.get('graph', {})
        status = data.get('status', 'pending')
        assignment_info = data.get('assignment_info', {})
        compiled_graph_data = data.get('compiled_graph_data', {})
        metadata = data.get('metadata', {})

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
            compiled_graph_data=compiled_graph_data,
            metadata=metadata
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
            'compiled_graph_data': self.compiled_graph_data,
            'metadata': self.metadata
        }


@dataclass
class vDAGController:
    vdag_controller_id: str = ''
    vdag_uri: str = ''
    public_url: str = ''
    cluster_id: str = ''
    metadata: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    search_tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'vDAGController':
        return cls(
            vdag_controller_id=data.get('vdag_controller_id', ''),
            vdag_uri=data.get('vdag_uri', ''),
            metadata=data.get('metadata', {}),
            config=data.get('config', {}),
            public_url=data.get('public_url', ''),
            search_tags=data.get('search_tags', []),
            cluster_id=data.get('cluster_id', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'vdag_controller_id': self.vdag_controller_id,
            'vdag_uri': self.vdag_uri,
            'metadata': self.metadata,
            'config': self.config,
            'public_url': self.public_url,
            'search_tags': self.search_tags,
            'cluster_id': self.cluster_id
        }