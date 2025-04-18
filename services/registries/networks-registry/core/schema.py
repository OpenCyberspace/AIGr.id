from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class NetworkObject:
    network_id: str = ''
    network_name: str = ''
    metadata: Dict[str, Any] = field(default_factory=dict)
    services_map: Dict[str, str] = field(default_factory=dict)
    policies: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkObject':
        return cls(
            network_id=data.get('network_id', ''),
            network_name=data.get('network_name', ''),
            metadata=data.get('metadata', {}),
            services_map=data.get('services_map', {}),
            policies=data.get('policies', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'network_id': self.network_id,
            'network_name': self.network_name,
            'metadata': self.metadata,
            'services_map': self.services_map,
            'policies': self.policies
        }
