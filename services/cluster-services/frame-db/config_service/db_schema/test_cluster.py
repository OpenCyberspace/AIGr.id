import pymodm
from cluster_config import *

MONGO_URI = "mongodb://localhost:27017/framedb?authSource=admin"

pymodm.connect(MONGO_URI)

connection = FramedbClusterInfo(
    cluster_name = "framedb-0",
    node_tag = "framedb-0",
    svc_name = "framedb-0-redis",
    svc_host = "10.101.224.56",
    metrics_svc = "framedb-0-redis-metrics",
    namespace = "framedb",
    master_port = 6379,
    sentinel_port = 26379,
    metrics_port = 9191,
    clusterPods = ["framedb-0-redis-node-0", "framedb-0-redis-node-1", "framedb-0-redis-node-2", "framedb-0-redis-node-3"]
)

connection.save()
#print(BaseRedisStructure.objects.get({"_id" : "db-0"}).to_son().to_dict())
