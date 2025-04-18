from dataclasses import dataclass, field
from typing import Dict, List
import uuid

@dataclass
class InferenceServer:
    inference_server_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    inference_server_name: str = ''
    inference_server_metadata: Dict[str, str] = field(default_factory=dict)
    inference_server_tags: List[str] = field(default_factory=list)
    inference_server_public_url: str = ''

    @classmethod
    def from_dict(cls, data: Dict) -> "InferenceServer":
        return cls(
            inference_server_id=data.get("inference_server_id", str(uuid.uuid4())),
            inference_server_name=data.get("inference_server_name", ""),
            inference_server_metadata=data.get("inference_server_metadata", {}),
            inference_server_tags=data.get("inference_server_tags", []),
            inference_server_public_url=data.get("inference_server_public_url", "")
        )

    def to_dict(self) -> Dict:
        return {
            "inference_server_id": self.inference_server_id,
            "inference_server_name": self.inference_server_name,
            "inference_server_metadata": self.inference_server_metadata,
            "inference_server_tags": self.inference_server_tags,
            "inference_server_public_url": self.inference_server_public_url
        }
