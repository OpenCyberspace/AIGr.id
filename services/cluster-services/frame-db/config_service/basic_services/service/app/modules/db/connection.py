import pymodm
import redis

import logging
logging = logging.getLogger("MainLogger")

from ...configs import settings
from .basic_config import *

class FramedbConfigConnector:

    def __init__(self) :
        URI = settings.MONGO_URI
        DB_NAME = settings.DB_NAME
        pymodm.connect("{}/{}?authSource=admin".format(URI, DB_NAME))

        logging.info("FramedbConfigConnector - Connected to database")

        #print(dir(BaseRedisStructure))
    
    
    def getRedisConnection(self, framedbId) :

        try:
            connection = BaseRedisStructure.objects.get({"_id" : framedbId})

            #get host, port and password 
            discoveryDetails = connection.discovery
            host = discoveryDetails.host 
            port = discoveryDetails.port 
            password = discoveryDetails.password if discoveryDetails.password else None

            redisConnection = redis.Redis(
                host = host,
                port = port,
                password = password,
                db = 0
            )

            return True, redisConnection
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
