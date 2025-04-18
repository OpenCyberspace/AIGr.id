from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
import uuid

@dataclass
class GlobalTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_data: Dict[str, Any] = field(default_factory=dict)
    task_type: str = field(default_factory=str)
    task_update_timestamp: int = field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    task_create_timestamp: int = field(default_factory=lambda: int(datetime.utcnow().timestamp()))
    task_status: str = field(default='pending')
    task_status_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalTask':
        return cls(
            task_id=data.get('task_id', str(uuid.uuid4())),
            task_data=data.get('task_data', {}),
            task_type=data.get('task_type', {}),
            task_update_timestamp=data.get('task_update_timestamp', int(datetime.utcnow().timestamp())),
            task_create_timestamp=data.get('task_create_timestamp', int(datetime.utcnow().timestamp())),
            task_status=data.get('task_status', 'pending'),
            task_status_data=data.get('task_status_data', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_data': self.task_data,
            'task_type': self.task_type,
            'task_update_timestamp': self.task_update_timestamp,
            'task_create_timestamp': self.task_create_timestamp,
            'task_status': self.task_status,
            'task_status_data': self.task_status_data
        }