import pymodm
import redis
from ...configs import settings
from .basic_config import * 

import logging
logging = logging.getLogger("MainLogger")


# A list of available Redis configs that can be applied,
# You can provide a new config support by adding entries to this dict
configsSettings = {
    "failover-timeout" : {"type" : "integer", "min" : 1000, "max" : 600000, "command" : "failover-timeout" },
    "down-after-milliseconds" : {"type" : "integer", "min" : 1000, "max" : 600000, "command" : "down-after-milliseconds"},
    "parallel-syncs" : {"type" : "integer", "min" : 1, "max" : 100, "command" : "parallel-syncs"}
}

class ConfigRestorer :

    def __init__(self):
        pymodm.connect("{}/{}?authSource=admin".format(
            settings.MONGO_URI, settings.DB_NAME
        ))
    

    def __write_configs(self, connection : redis.Redis, configSet : dict, master : str) :

        for configName, value in configSet.items() :
            if not configName in configsSettings :
                continue

            config_command = configsSettings[configName]['command']
            connection.execute_command("SENTINEL", "SET", master, config_command, str(value))
            
    def restoreConfigs(self, framedb_id) :

        try:

            connection = BaseRedisStructure.objects.get({"_id" : framedb_id})
            discovery = connection.discovery

            host = discovery.sentinalHost 
            port = discovery.sentinalPort 
            password = discovery.sentinalPassword

            master = discovery.sentinalMasterName

            redisConnection = redis.Redis(
                host = host,
                port = port,
                password = password
            )

            configs = connection.config.basicConfig
            #for each config, restore  the settings:

            self.__write_configs(redisConnection, configs, master)
            return True, "Wrote configs"

            
        except Exception as e:
            logging.error(e)
            return False, str(e)
