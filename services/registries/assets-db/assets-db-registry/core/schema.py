from dataclasses import dataclass, field
from typing import Dict, List
import uuid

@dataclass
class AssetRegistry:
    asset_registry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_registry_name: str = ''
    asset_registry_metadata: Dict[str, str] = field(default_factory=dict)
    asset_registry_tags: List[str] = field(default_factory=list)
    asset_registry_public_url: str = ''

    @classmethod
    def from_dict(cls, data: Dict) -> "AssetRegistry":
        return cls(
            asset_registry_id=data.get("asset_registry_id", str(uuid.uuid4())),
            asset_registry_name=data.get("asset_registry_name", ""),
            asset_registry_metadata=data.get("asset_registry_metadata", {}),
            asset_registry_tags=data.get("asset_registry_tags", []),
            asset_registry_public_url=data.get("asset_registry_public_url", "")
        )

    def to_dict(self) -> Dict:
        return {
            "asset_registry_id": self.asset_registry_id,
            "asset_registry_name": self.asset_registry_name,
            "asset_registry_metadata": self.asset_registry_metadata,
            "asset_registry_tags": self.asset_registry_tags,
            "asset_registry_public_url": self.asset_registry_public_url
        }