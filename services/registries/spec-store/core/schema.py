from dataclasses import dataclass, field
from typing import Dict, List, Any

@dataclass
class SpecStoreObject:
    specUri: str = ''
    specType: str = ''
    specName: str = ''
    specVersion: Dict[str, str] = field(default_factory=lambda: {"version": "", "tag": ""})
    specDescription: str = ''
    specMetadata: Dict[str, Any] = field(default_factory=dict)
    specTags: List[str] = field(default_factory=list)
    specData: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpecStoreObject':
        spec_name = data.get('specName', '')
        spec_version = data.get('specVersion', {"version": "", "tag": ""})
        spec_uri = f"{spec_name}:{spec_version.get('version', '')}-{spec_version.get('tag', '')}"
        
        return cls(
            specUri=spec_uri,
            specType=data.get('specType', ''),
            specName=spec_name,
            specVersion=spec_version,
            specDescription=data.get('specDescription', ''),
            specMetadata=data.get('specMetadata', {}),
            specTags=data.get('specTags', []),
            specData=data.get('specData', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'specUri': self.specUri,  # Precomputed during initialization
            'specType': self.specType,
            'specName': self.specName,
            'specVersion': self.specVersion,
            'specDescription': self.specDescription,
            'specMetadata': self.specMetadata,
            'specTags': self.specTags,
            'specData': self.specData
        }
