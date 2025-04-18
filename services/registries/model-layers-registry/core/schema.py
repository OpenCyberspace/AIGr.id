from dataclasses import dataclass, field
from typing import Dict, List, Any

@dataclass
class ModelLayerObject:
    model_layer_hash: str = ''
    model_asset_id: str = ''
    model_component_registry_uri: str = ''
    model_layer_public_url: str = ''
    model_layer_metadata: List[Dict[str, Any]] = field(default_factory=list)
    model_layer_rank: int = 0
    model_world_size: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelLayerObject':
        return cls(
            model_layer_hash=data.get('model_layer_hash', ''),
            model_asset_id=data.get('model_asset_id', ''),
            model_component_registry_uri=data.get('model_component_registry_uri', ''),
            model_layer_public_url=data.get('model_layer_public_url', ''),
            model_layer_metadata=data.get('model_layer_metadata', []),
            model_layer_rank=data.get('model_layer_rank', 0),
            model_world_size=data.get('model_world_size', 0)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_layer_hash': self.model_layer_hash,
            'model_asset_id': self.model_asset_id,
            'model_component_registry_uri': self.model_component_registry_uri,
            'model_layer_public_url': self.model_layer_public_url,
            'model_layer_metadata': self.model_layer_metadata,
            'model_layer_rank': self.model_layer_rank,
            'model_world_size': self.model_world_size
        }
