from dataclasses import dataclass, field, asdict
from typing import Dict, List


@dataclass
class SplitsDeploymentEntry:
    rank_0_cluster_id: str
    cluster_id: List[str]
    deployment_name: str  
    nnodes: int
    common_params: Dict
    metadata: Dict
    per_rank_params: List[Dict]
    namespace: str = "splits"
    multi_cluster: bool = False
    platform: str = "torch"

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "SplitsDeploymentEntry":
       
        return SplitsDeploymentEntry(
            rank_0_cluster_id=data['rank_0_cluster_id'],
            cluster_id=data["cluster_id"],
            deployment_name=data["deployment_name"],
            nnodes=data["nnodes"],
            common_params=data["common_params"],
            per_rank_params=data["per_rank_params"],
            namespace=data.get("namespace", "splits"),
            multi_cluster=data.get("multi_cluster", False),
            platform=data.get("platform", "torch"),
            metadata=data.get('metadata', {})
        )
