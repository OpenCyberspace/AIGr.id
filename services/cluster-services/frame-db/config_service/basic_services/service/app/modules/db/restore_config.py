import pymodm
import redis
from ...configs import settings
from .basic_config import * 

import logging
logging = logging.getLogger("MainLogger")


# A list of available Redis configs that can be applied,
# You can provide a new config support by adding entries to this dict
configsSettings = {
    "timeout" : {"type" : "integer", "min" : 0, "max" : 3600, "command" : "timeout", "category" : "network"},
    "databases" : {"type" : "integer", "min" : 0, "max" : 64, "command" : "databases", "category" : "general"},
    "maxclients" : {"type" : "integer", "min" : 128, "max" : "65536", "command" : "maxclients", "category" : "general"},
    "maxmemory" : {"type" : "float", "min" : 0, "max" : 1.0, "maxmemory" : "maxmemory", "category" : "memory"},
    "maxmemory-policy" : {
        "type" : "string", 
        "command" : "maxmemory-policy",
        "choices" : ["volatile-lru", "allkeys-lru", "volatile-random", "allkeys-random", "volatile-ttl", "noeviction"],
        "category" : "memory"
    },
    "maxmemory-samples" : {"type" : "integer", "min" : 2, "max" : 10, "command" : "maxmemory-samples", "category" : "memory"},
    "enable-swap" : {"type" : "string", "choices" : ["yes", "no"], "command" : "vm-enabled", "category" : "memory"},
    "vm-swap-file" : {"type" : "string", "command" : "vm-swap-file", "command" : "vm-swap-file", "category" : "memory"},
    "vm-max-memory" : {"type" : "float", "min" : 0, "max" : 1.0, "command" : "vm-max-memory", "category" : "memory"},
    "vm-max-threads" : {"type" : "integer", "min" : 0, "max" : 16, "command" : "vm-max-threads", "category" : "memory"},
    "disable-command" : {"type" : "string", "category" : "security", "command" : "rename-command", "require_restart" : True},
    "enable-command" : {"type" : "string", "category" : "security", "command" : "rename-command", "require_restart" : True},
    "tcp-backlog" : {"type" : "integer", "command" : "tcp-backlog", "category" : "network"},
    "slowlog-max-len" : {"type" : "integer", "command" : "slowlog-max-len", "category" : "logging"},
    "slowlog-log-slower-than" : {"type" : "integer", "command" : "slowlog-log-slower-than", "category" : "logging"},
    "logfile" : {"type" : "string", "command" : "logfile", "category" : "logging"},
    "loglevel" : {"type" : "string", "choices" : ["warning", "notice", "verbose", "debug"], "command" : "loglevel", "category" : "logging"},
    "save" : {"type" : "string", "command" : "save"},
    "rdbchecksum" : {"type" : "string", "command" : "rdbchecksum"},
    "rdbcompression" : {"type" : "string", "command" : "rdbcompression"}
}

class ConfigRestorer :

    def __init__(self):
        pymodm.connect("{}/{}?authSource=admin".format(
            settings.MONGO_URI, settings.DB_NAME
        ))
    

    def __write_configs(self, connection : redis.Redis, configSet : dict) :

        for configName, value in configSet.items() :
            if not configName in configsSettings :
                continue

            config_command = configsSettings[configName]['command']
            connection.config_set(config_command, value)
            
    def restoreConfigs(self, framedb_id) :

        try:

            connection = BaseRedisStructure.objects.get({"_id" : framedb_id})
            discovery = connection.discovery

            host = discovery.host 
            port = discovery.port 
            password = discovery.password

            redisConnection = redis.Redis(
                host = host,
                port = port,
                password = password
            )

            configs = connection.config.basicConfig
            #for each config, restore  the settings:

            self.__write_configs(redisConnection, configs)
            return True, "Wrote configs"

            
        except Exception as e:
            logging.error(e)
            return False, str(e)
