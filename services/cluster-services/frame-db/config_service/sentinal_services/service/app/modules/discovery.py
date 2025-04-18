from fastapi import APIRouter, Request
from .db.connection import SentinelConnector
from .sentinel_api import SentinelApi

from .utils import with_logging, send_error_message, send_success_message, validate_json_fields


import logging
logging = logging.getLogger("MainLogger")

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


class DiscoveryController :

    @staticmethod
    def DiscoverMaster(framedb_id : str) :
        ret, connection, masterName = SentinelConnector.GetSentinelConnection(
            framedb_id
        )

        if not ret :
            return False, "Failed to get sentinel connection for {}".format(framedb_id)
        
        #discover master:
        ret, masterData = SentinelApi.GetMasterAddress(connection, masterName)
        if not ret :
            return False, str(masterData)
        return True, masterData
    
    @staticmethod
    def DiscoverClusterMaster(clusterName : str) :

        ret, connection, masterName = SentinelConnector.GetClusterConnection(
            clusterName
        )
        if not ret :
            return False, "Failed to get sentinel connection for {}".format(clusterName)
        
        #discover master 
        ret, masterData = SentinelApi.GetMasterAddress(connection, masterName)
        if not ret :
            return False, str(masterData)
        return True, masterData
    
    @staticmethod
    def DiscoverSlaves(framedb_id : str) :
        ret, connection, masterName = SentinelConnector.GetSentinelConnection(
            framedb_id
        )
        if not ret :
            return False, "Failed to get sentinel connection for {}".format(framedb_id)
        #discover slaves:
        ret, slaves = SentinelApi.GetSlavesAddress(connection, masterName)
        if not ret :
            return False, str(slaves)
        
        return True, slaves
    
    @staticmethod
    def GetClusterData(framedb_id : str) :

        ret, connection, masterName = SentinelConnector.GetSentinelConnection(
            framedb_id
        )
        if not ret :
            return False, "Failed to get sentinel connection for {}".format(framedb_id)
        
        #discover master + slaves
        ret, masterData = SentinelApi.GetMasterAddress(connection, masterName)
        if not ret :
            return False, str(masterData)
        
        ret, slaveData = SentinelApi.GetSlavesAddress(connection, masterName)
        if not ret :
            return False, str(slaveData)
        
        return True, {"clusterInfo" : {"master" : masterData, "slaves" : slaveData, "masterName" : masterName}}
    


discoveryRouter = APIRouter()
@with_logging("/discovery/getMaster")
@discoveryRouter.post("/getMaster")
async def getMaster(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['framedb_id'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = DiscoveryController.DiscoverMaster(body['framedb_id'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/discovery/getSlaves")
@discoveryRouter.post("/getSlaves")
async def getSlaves(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['framedb_id'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = DiscoveryController.DiscoverSlaves(body['framedb_id'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/discovery/getClusterInfo")
@discoveryRouter.post("/getClusterInfo")
async def getClusterInfo(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['framedb_id'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = DiscoveryController.GetClusterData(body['framedb_id'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/discovery/getClusterMaster")
@discoveryRouter.post("/getClusterMaster")
async def getClusterMaster(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['clusterName'])
    if not ret :
        return send_error_message("Missing field " + field)
    ret, result = DiscoveryController.DiscoverClusterMaster(clusterName = body['clusterName'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)