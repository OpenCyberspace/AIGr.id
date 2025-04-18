import os 
from redis_router import RedisRouter, FrameValidator
import time
import signal

updateChannelData = {
        "host" : "localhost",
        "port" : 6379,
        "password" : "Friends123#",
        "db" : 0,
        "isSentinel" : False
}

routingService = {
        "uri" : "http://localhost:8000",
        "api" : "/routing/getMapping",
        "update_api" : "/routing/updateMapping"
}

router = RedisRouter(
    sourceId = 'test-local-3',
    routingService = routingService,
    enableUpdates = True,
    updateChannelData = updateChannelData,
    asynchronous = True
)


validator = FrameValidator('test-local-3', validator_rule_fn = None, use_own_keys = False)


index = 0
data = os.urandom(300 * 1024)

validation_meta_rules = {
        "width" : 1920,
        "height" : 1080,
        "type" : "image/jpeg"
}


while True :

    #data = os.urandom(300 *  1024)
    if validator.is_valid_frame(str(index), None, router, validation_meta_rules) :
        router.put('test', str(index), data)

    time.sleep(1/25)

    index +=1
