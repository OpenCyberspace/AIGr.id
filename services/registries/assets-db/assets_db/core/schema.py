from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AssetObject:
    asset_uri: str = ''
    asset_name: str = ''
    asset_id: str = ''
    assets_db_id: str = ''
    asset_version: Dict[str, str] = field(
        default_factory=lambda: {"version": "", "tag": ""})
    asset_metadata: Dict[str, str] = field(default_factory=dict)
    asset_public_url: str = ''
    asset_file_info: Dict[str, str] = field(default_factory=dict)
    asset_tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "AssetObject":
        asset_name = data.get("asset_name", "")
        asset_version = data.get("asset_version", {}).get("version", "")
        asset_tag = data.get("asset_version", {}).get("tag", "")

        inferred_asset_uri = (
            f"{asset_name}:{asset_version}-{asset_tag}"
            if asset_name and asset_version and asset_tag
            else ""
        )

        return cls(
            asset_uri=inferred_asset_uri,
            asset_name=asset_name,
            asset_version=data.get(
                "asset_version", {"version": "", "tag": ""}),
            asset_metadata=data.get("asset_metadata", {}),
            asset_public_url=data.get("asset_public_url", ""),
            asset_file_info=data.get("asset_file_info", {}),
            asset_tags=data.get("asset_tags", []),
            asset_id=data.get('asset_id', '')
        )

    def to_dict(self) -> Dict:
        return {
            "asset_uri": self.asset_uri,
            "asset_name": self.asset_name,
            "asset_version": self.asset_version,
            "asset_metadata": self.asset_metadata,
            "asset_public_url": self.asset_public_url,
            "asset_file_info": self.asset_file_info,
            "asset_tags": self.asset_tags,
            "asset_id": self.asset_id
        }
