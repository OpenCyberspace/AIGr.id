from dataclasses import dataclass, field
from typing import Dict, List, Any
import uuid

@dataclass
class SplitRunnerObject:
    split_runner_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    split_runner_public_url: str = ''
    split_runner_metadata: Dict[str, Any] = field(default_factory=dict)
    split_runner_public_host: str = ''
    split_runner_tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SplitRunnerObject':
        return cls(
            split_runner_id=data.get('split_runner_id', str(uuid.uuid4())),
            split_runner_public_url=data.get('split_runner_public_url', ''),
            split_runner_metadata=data.get('split_runner_metadata', {}),
            split_runner_public_host=data.get('split_runner_public_host', ''),
            split_runner_tags=data.get('split_runner_tags', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'split_runner_id': self.split_runner_id,
            'split_runner_public_url': self.split_runner_public_url,
            'split_runner_metadata': self.split_runner_metadata,
            'split_runner_public_host': self.split_runner_public_host,
            'split_runner_tags': self.split_runner_tags
        }
