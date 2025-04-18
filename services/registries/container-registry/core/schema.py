from dataclasses import dataclass, field
from typing import Dict, List, Any
import uuid

from dataclasses import dataclass, field
from typing import Dict, List
import uuid

@dataclass
class ContainerRegistry:
    container_registry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    container_registry_name: str = ''
    container_registry_metadata: Dict[str, Any] = field(default_factory=dict)
    container_registry_tags: List[str] = field(default_factory=list)
    container_registry_public_url: str = ''
    container_registry_image_prefix: str = '' 
    container_registry_config: Dict[str, Any] = field(default_factory=dict)
    container_registry_storage_info: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict) -> "ContainerRegistry":
        return cls(
            container_registry_id=data.get("container_registry_id", str(uuid.uuid4())),
            container_registry_name=data.get("container_registry_name", ""),
            container_registry_metadata=data.get("container_registry_metadata", {}),
            container_registry_tags=data.get("container_registry_tags", []),
            container_registry_public_url=data.get("container_registry_public_url", ""),
            container_registry_image_prefix=data.get("container_registry_image_prefix", ""),
            container_registry_config=data.get("container_registry_config", {}),
            container_registry_storage_info=data.get('container_registry_storage_info', {})
        )

    def to_dict(self) -> Dict:
        return {
            "container_registry_id": self.container_registry_id,
            "container_registry_name": self.container_registry_name,
            "container_registry_metadata": self.container_registry_metadata,
            "container_registry_tags": self.container_registry_tags,
            "container_registry_public_url": self.container_registry_public_url,
            "container_registry_image_prefix": self.container_registry_image_prefix,
            "container_registry_config": self.container_registry_config,
            "container_registry_storage_info": self.container_registry_storage_info
        }
