from .sentinel_api import SentinelApi
from .db.connection import SentinelConnector
from .db.save_config import ConfigSaver
from .db.restore_config import ConfigRestorer

from .utils import send_success_message, send_error_message, validate_json_fields, with_logging
from fastapi import APIRouter, Request

import logging
logging = logging.getLogger("MainLogger")

configs = {
    "failover-timeout" : {"type" : "integer", "min" : 1000, "max" : 600000, "command" : "failover-timeout" },
    "down-after-milliseconds" : {"type" : "integer", "min" : 1000, "max" : 600000, "command" : "down-after-milliseconds"},
    "parallel-syncs" : {"type" : "integer", "min" : 1, "max" : 100, "command" : "parallel-syncs"}
}

def log_request(request : Request, dictPayload : dict = None) :

    url = request.url.path
    logging.info(
        "{} got hit".format(url), 
        extra = {
            "client_host" : request.client.host,
            "client_port" : request.client.port,
            "payload" : str(dictPayload) if dictPayload else None,
            "endpoint" : url
        }
    )

class SentinelConfiguration :

    @staticmethod
    def validate_config(parameter, value) : 
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
    
    @staticmethod
    def SaveToDB(framedb_id, parameter, value) :
        ret, result = ConfigSaver().updateConfig(
            framedb_id, parameter, value
        )
        if not ret :
            return False, str(result)
        
        return True, "saved config to db"

    @staticmethod
    def GetCurrentConfig(framedb_id) :
        ret, connection, masterName = SentinelConnector.GetRedisConnection(
            framedb_id
        )

        if not ret :
            return False, str(connection)
        #get current config by executing sentinel master <master-name> command

        try:
            print('In config service')
            output = connection.execute_command("sentinel", "master", masterName)

            #parse outputs

            formattedConfigOutput = {}
            for idx in range(0, len(output) - 1, 2) :
                key = str(output[idx], 'utf-8')
                value = str(output[idx + 1], 'utf-8')
                formattedConfigOutput[key] = value

            return True, formattedConfigOutput
        except Exception as e:
            raise e
            return False, str(e)
    
    @staticmethod
    def SetConfigParameter(framedb_id, configName, value) :

        ret, message = SentinelConfiguration.validate_config(configName, value)
        if not ret :
            return False, "validation failed"
        
        #set command
        ret, redisConnection, masterName = SentinelConnector.GetRedisConnection(
            framedb_id
        )
        if not ret :
            return False, "Failed to connect to sentinal for {}".format(configName)
        
        try:
            command = configs[configName]['command']
            status = redisConnection.execute_command(
                "SENTINEL", "SET", masterName, command, str(value)
            )

            if str(status, "utf-8") == "OK" :
                #save config to database
                ret, result = SentinelConfiguration.SaveToDB(
                    framedb_id, configName, str(value)
                )
                return True, "Updated config and saved to database"
            
            return False, "Failed to save config"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetOptions() :
        return True,  configs

    
configurationRouter = APIRouter()

@with_logging("/config/setConfig")
@configurationRouter.post("/setConfig")
async def setConfig(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['framedb_id', 'configName', 'value'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = SentinelConfiguration.SetConfigParameter(
        body['framedb_id'], body['configName'], body['value']
    )
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/config/getConfig")
@configurationRouter.post("/getConfig")
async def getConfig(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['framedb_id'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = SentinelConfiguration.GetCurrentConfig(body['framedb_id'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/config/getOptions")
@configurationRouter.get("/getOptions")
async def getOptions(request : Request) :

    log_request(request)

    ret, result = SentinelConfiguration.GetOptions()
    if not ret :
        return send_error_message(result)

    return send_success_message(result)

@with_logging("/config/restore")
@configurationRouter.post("/restore")
async def restoreConfig(body : dict, request : Request) :

    log_request(request, body)

    ret, fields = validate_json_fields(body, ['framedb_id'])
    if not ret :
        return send_error_message("Missing field " + fields)
    ret, result = ConfigRestorer().restoreConfigs(body['framedb_id'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)