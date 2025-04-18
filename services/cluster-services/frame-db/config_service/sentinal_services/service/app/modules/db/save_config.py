from redis import Redis
import pymodm
from .basic_config import * 
from ...configs import settings

import logging
logging = logging.getLogger("MainLogger")

class ConfigSaver :

    def __init__(self) :
        pymodm.connect("{}/{}?authSource=admin".format(
            settings.MONGO_URI, settings.DB_NAME
        ))
    
    def updateConfig(self, framedb_id, key, value) :

        try:

            connection = BaseRedisStructure.objects.get({"_id" : framedb_id})
            if connection :

                #get its config details
                config = connection.config.basicConfig
                if not config :
                    config = {}
                config[key] = value

                connection.config.basicConfig = config
                connection.save()
            return True, "Updated config details"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
