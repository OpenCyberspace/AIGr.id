import pymodm
from basic_config import *

MONGO_URI = "mongodb://localhost:27017/framedb?authSource=admin"

pymodm.connect(MONGO_URI)
connection = BaseRedisStructure(
    framedbId = "db-2",
    clusterId = "cluster-1",
    role = "master",
    discovery = Discovery(
        host = "127.0.0.1",
        port = 6380,
        password = "Friends123#",
        clusterServiceHost = "127.0.0.1",
        clusterServicePort = 6380,
        sentinalPassword = 'Friends123#',
        sentinalPort = 26379,
        sentinalHost = '127.0.0.1',
        sentinalMasterName = 'mymaster',
        hostAddress = '127.0.0.1'
    ),
    config = {}
)

connection.save()
#print(BaseRedisStructure.objects.get({"_id" : "db-0"}).to_son().to_dict())
