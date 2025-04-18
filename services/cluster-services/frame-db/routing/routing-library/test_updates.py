from redis_router import RedisRouter
import time


routingService = RedisRouter(
    sourceId = "test",
    routingService = {
        "uri" : "http://localhost:8000",
        "api" : "/routing/getMapping"
    },
    enableUpdates = True,
    updateChannelData = {
        "host" : "localhost",
        "port" : 6379,
        "password" : "Friends123#",
        "db" : 0
    }
)



while True :
    time.sleep(10)