import redis
import logging

logging = logging.getLogger("Mainlogging")

from ..db.connection import FramedbConfigConnector
from ..db.save_config import ConfigSaver

# A list of available Redis configs that can be applied,
# You can provide a new config support by adding entries to this dict
configs = {
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
    "loglevel" : {"type" : "string", "choices" : ["warning", "notice", "verbose", "debug"], "command" : "loglevel", "category" : "logging"}
}


class BasicRedisConfig :

    def __init__(self, test_mode = False, test_connection = None) :
        logging.info("Initialized RedisConfig module")

        self.test_mode = test_mode
        self.test_connection = test_connection

        self.framedbConnector = FramedbConfigConnector()
    
    def __get_connection_from_db(self, framedb_id) :
        return self.framedbConnector.getRedisConnection(framedb_id)
    
    def __validate_rules(self, parameter, value) :
        if parameter not in configs :
            return False, "Unknown parameter"
        #validate rule by its type :
        parameter_rules = configs[parameter]
        if parameter_rules['type'] == 'float' and type(value) == float :
            if not ('min' in parameter_rules ) :
                if not (value >= parameter_rules['min']):
                    return False, "value is less than minimum" 
            if not ('max' in parameter_rules):
                if not (value <= parameter_rules['max']) :
                    return False, "value is greater than maximum"
            return True, "Validation passed"
        
        if parameter_rules['type'] == 'integer' and type(value) == int :
            if not ('min' in parameter_rules ) :
                if not (value >= parameter_rules['min']):
                    return False, "value is less than minimum" 
            if not ('max' in parameter_rules):
                if not (value <= parameter_rules['max']) :
                    return False, "value is greater than maximum"
            return True, "Validation passed"
        
        if parameter_rules['type'] == 'string' and type(value) == str :
            if 'choices' in parameter_rules :
                if value not in parameter_rules['choices'] :
                    return True, "Value not in choices"
            
            return True, "Validation passed"
        
        return False, "Validation failed, unknown value type"
    

    def __convert_dtype(self, result_dict, rules_dict) :

        dtype = None
        if rules_dict['type'] == "integer" :
            dtype = int 
        elif rules_dict['type'] == "float" :
            dtype = float
        elif rules_dict['type'] == "string" :
            dtype = str 
        elif rules_dict['type'] == 'bool' :
            dtype = bool

        for result in result_dict :
            result_dict[result] = dtype(result_dict[result])
            
        return result_dict
    
    def __save_to_db(self, framedb_id, parameter, value) :

        ret, result = ConfigSaver().updateConfig(
            framedb_id, 
            parameter,
            str(value)
        )

        if not ret :
            return False, str(result)
        return True, "config updated and saved to db"
        

    def setConfig(self, framedb_id, parameter, value) :

        ret, message = self.__validate_rules(parameter, value) 
        if not ret :
            logging.error(
                "Validation failed for parameter={} value={}".format(parameter, value),
                extra = {"error_type" : "validation_fail", "message" : message}
            )
            return False, message
        
        parameter_rules = configs[parameter]
        connection = None 
        if self.test_mode and self.test_connection :
            connection = self.test_connection
        else:
            status, connection = self.__get_connection_from_db(framedb_id)
            if not status :
                return False, str(connection)

        try:
            result = connection.config_set(parameter_rules['command'], value)
            if result:
                ret, result = self.__save_to_db(framedb_id, parameter, value)
                if not ret :
                    return False, str(result)
                return True, "Config {} set successful".format(parameter)
            return False, "Config {} failed".format(parameter)
        except Exception as e:
            logging.error("Redis error", extra = {"error_type" : "redis_error", "error_message" : str(e)})
            return False, str(e) 


    def getConfig(self, framedb_id, parameter) :
        
        #gets config value
        if not parameter in configs :
            return False, "Unknwon config name " + parameter
        
        parameter_rules = configs[parameter]
        
        connection = None
        if self.test_mode and self.test_connection :
            connection = self.test_connection
        else :
            status, connection = self.__get_connection_from_db(framedb_id)
            if not status :
                return False, str(connection)
        
        #execute config get command :
        try:
            result = connection.config_get(parameter_rules['command'])
            return True, self.__convert_dtype(result, parameter_rules)
        except Exception as e:
            logging.error("Redis error", extra = {"error_type" : "redis_error", "error_message" : str(e)})
            return False, str(e)

    def getConfigsAvailable(self) :
        return True, configs 

    def getConfigsByCategory(self, category) :
        filterd_configs = {k : v for k, v in configs.items() if v['category'] == category}
        return True, filterd_configs

