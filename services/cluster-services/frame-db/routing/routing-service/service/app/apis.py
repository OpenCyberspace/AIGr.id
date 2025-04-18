from fastapi import APIRouter, Request
import logging

from .db import db_api
from .db.discoverMaster import SentinelMasterDiscovery
from .update import PubSubUpdater
from .update import PubSubUpdater

from .utils import with_logging, send_success_message, send_error_message, validate_json_fields


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

def log_routing_table_update(operation, sourceId, nodeTag) :

    logging.info(
        "{} got updated".format(sourceId),
        extra = {
            "type" : "routing_table_update",
            "operation" : operation,
            "sourceId" : sourceId,
            "nodeTag" : nodeTag 
        }
    )

class RoutingServiceApis :

    @staticmethod
    def AddSourceMapping(sourceId, nodeTag, metadata = {}) :

        print(metadata)

        try:
            ret, framedbSource, masterIP = SentinelMasterDiscovery.DiscoverMaster(
                nodeTag
            )

            if not ret :
                return False, framedbSource
            
            ret, result = db_api.MappingDBApi.CreateNewMapping(sourceId, framedbSource, nodeTag, masterIP, metadata = metadata)
            if not ret :
                return False, result
            
            frameDB = {
                "serviceIp" : framedbSource.svc_host,
                "sentinelPort" : framedbSource.sentinel_port,
                "serviceName" : framedbSource.svc_name,
                "redisPort" : framedbSource.master_port,
                "masterIP" : masterIP,
                "nodeTag" : nodeTag,
                "clusterName" : framedbSource.cluster_name,
                "metadata" : metadata
            }

            ret, result = PubSubUpdater.UpdateAddition(sourceId, [frameDB])
            if not ret :
                logging.error("Failed to Pub-Sub")
                return False, str(result)
        

            #update the framedb-to-source mapping:
            ret, result = db_api.FramedbToSourceApi.AddEntry(framedbSource.cluster_name, sourceId, nodeTag)

            if not ret :
                return False, result
            
            return True, result

        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def UpdateMapping(sourceId, nodeTag) :

        try:
            
            ret, nodeData = SentinelMasterDiscovery.RediscoverMaster(sourceId, nodeTag)
            if not ret :
                return False, nodeData
            
            nodeDataDict = nodeData.to_son().to_dict()

            ret, result = PubSubUpdater.UpdateAddition(sourceId, [nodeDataDict])
            if not ret :
                return False, "Failed to send pub-sub updates"
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)


    @staticmethod
    def RemoveSourceMapping(sourceId, nodeTag) :
        
        try:
            ret, result, cluster_name = db_api.MappingDBApi.RemoveMapping(sourceId, nodeTag)
            if not ret :
                return False, result

            ret, result = PubSubUpdater.UpdateRemove(sourceId, [nodeTag])
            if not ret :
                return False, result
            
            ret, result = db_api.FramedbToSourceApi.RemoveEntry(cluster_name, sourceId, nodeTag)
            if not ret :
                return False, result

            return True, result
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetSourceMappings(sourceId) :
        try:
            ret, result = db_api.MappingDBApi.GetMappingForSource(sourceId)
            if not ret :
                return False, "No source {}".format(sourceId)
            return True, result
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetSourcesByFramedb(framedb) :

        try:

            ret, result = db_api.FramedbToSourceApi.GetSourcesWritingByDb(framedb)
            if not ret :
                return False, str(result)
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetSourcesByNode(nodeTag) :

        try:
            ret, result = db_api.FramedbToSourceApi.GetSourcesWritingByNode(nodeTag)
            if not ret :
                return False, str(result)
            return True, result
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def ReassignInstances(nodeTag, framedbId) :

        try:

            ret, sources = db_api.FramedbToSourceApi.GetSourcesAndRemove(framedbId)
            if not ret :
                logging.error("Failed to get sources list")
                return False, "Failed to get sources list"
            

            if len(sources) == 0 :
                return True, "No sources are writing to {} so no reassignment is possible".format(framedbId)
            
            ret, framedbSource, masterIP = SentinelMasterDiscovery.DiscoverMaster(nodeTag)
            if not ret :
                logging.error("Failed to discover master")
                return False, "Failed to discover master"
            
            ret, result = db_api.MappingDBApi.OverrideNewInstances(sources, framedbSource, masterIP, nodeTag)
            if not ret :
                logging.error("Failed to update DB")
                return False, "Failed to update DB"
            

            frameDB = {
                "serviceIp" : framedbSource.svc_host,
                "sentinelPort" : framedbSource.sentinel_port,
                "serviceName" : framedbSource.svc_name,
                "redisPort" : framedbSource.master_port,
                "masterIP" : masterIP,
                "nodeTag" : nodeTag,
                "clusterName" : framedbSource.cluster_name
            }

            ret, result = PubSubUpdater.UpdateMultiSources(sources, [frameDB])
            if not ret :
                logging.error("Failed to send pubs-sub update")
                return False, "Failed to send pubs-sub update"
            
            #update metadata
            ret, result = db_api.FramedbToSourceApi.AddEntries(framedbSource.cluster_name, sources)
            if not ret :
                logging.error("Failed to update metadata table")
                return False, "Failed to update metadata table"
            
            return True, "Updated and reassigned"

            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def ReassignSource(sourceId, nodeTag, framedbId) :

        try:

            ret, framedbSource, masterIP = SentinelMasterDiscovery.DiscoverMaster(nodeTag)
            if not ret :
                return False, "Failed to discover new master"
            
            ret, result = db_api.FramedbToSourceApi.RemoveEntry(framedbId, sourceId, nodeTag)
            if not ret :
                return False, "Failed to update metadata"

            #assigning the new master by first publishing its address
            frameDB = {
                "serviceIp" : framedbSource.svc_host,
                "sentinelPort" : framedbSource.sentinel_port,
                "serviceName" : framedbSource.svc_name,
                "redisPort" : framedbSource.master_port,
                "masterIP" : masterIP,
                "nodeTag" : nodeTag,
                "clusterName" : framedbSource.cluster_name
            }

            ret, result = PubSubUpdater.UpdateAddition(sourceId, [frameDB])
            if not ret :
                return False, "Failed to publish pub-sub updates"
            
            ret, result = db_api.MappingDBApi.OverrideNewInstances([sourceId], framedbSource, masterIP, nodeTag)
            if not ret :
                return False, "Failed to update routing table"
            
            ret, result = db_api.FramedbToSourceApi.AddEntry(framedbSource.cluster_name, sourceId, nodeTag)
            if not ret :
                return False, "Failed to update metadata"

            return True, "Reassigned source and published updates"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetLeastAssignedInstance(nodeTag) :

        try:

            ret, result = db_api.FramedbToSourceApi.GetLeastAssignedInstance(nodeTag)
            if not ret :
                logging.error(result)
                return False, result
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetMaxAssignedInstance(nodeTag) :

        try:

            ret, result = db_api.FramedbToSourceApi.GetMaxAssignedInstance(nodeTag)
            if not ret :
                logging.error(result)
                return False, result
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def UpdateMetadata(sourceId, nodeTag, metadata = {}) :

        try:

            ret, result = db_api.MappingDBApi.UpdateMetadata(sourceId, nodeTag, metadata)
            if not ret :
                return False, "Failed to update metadata in the db"
            
            #send pub-sub update
            ret, result = PubSubUpdater.UpdateMetadata(sourceId, nodeTag, metadata)
            if not ret :
                return False, result
            
            return True, "Updated metadata for {}--->{}".format(sourceId, nodeTag)
            
        except Exception as e:
            logging.error(e)
            return False, str(e) 
    
    @staticmethod
    def GetMappingMetadata(sourceId, nodeTag) :

        try:

            ret, result = db_api.MappingDBApi.GetMappingMetadata(sourceId, nodeTag)
            if not ret :
                logging.error(e)
                return False, result
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)


routingService = APIRouter()

@with_logging("/routing/getMapping")
@routingService.post("/getMapping")
async def getMapping(body : dict, request : Request) :
    log_request(request, body)

    ret, result = validate_json_fields(body, ['sourceId'])
    if not ret :
        return send_error_message(result)
    
    ret, result = RoutingServiceApis.GetSourceMappings(body['sourceId'])
    if not ret :
        return send_error_message(result)

    log_routing_table_update("fetch", body['sourceId'], None)
    return send_success_message(result)

@with_logging("/routing/createMapping")
@routingService.post("/createMapping")
async def createMapping(body : dict, request : Request) :
    log_request(request, body)

    ret, result = validate_json_fields(body, ['sourceId', 'nodeTag'])
    if not ret :
        return send_error_message(result)
    
    ret, result = RoutingServiceApis.AddSourceMapping(body['sourceId'], body['nodeTag'], body['metadata'] if 'metadata' in body else {})
    if not ret :
        return send_error_message(result)
    
    log_routing_table_update("add", body["sourceId"], body["nodeTag"])
    return send_success_message(result)

@with_logging("/routing/removeMapping")
@routingService.post("/removeMapping")
async def deleteMapping(body : dict, request : Request) :

    log_request(request, body)

    ret, result = validate_json_fields(body, ['sourceId', 'nodeTag'])
    if not ret :
        return send_error_message(result)
    
    ret, result = RoutingServiceApis.RemoveSourceMapping(body['sourceId'], body['nodeTag'])
    if not ret :
        return send_error_message(result)
    
    log_routing_table_update("remove", body["sourceId"], body["nodeTag"])
    return send_success_message(result)

@with_logging("/routing/updateMapping")
@routingService.post("/updateMapping")
async def updateMapping(body : dict, request : Request) :

    log_request(request, body)

    ret, result = validate_json_fields(body, ['sourceId', 'nodeTag'])
    if not ret :
        return send_error_message(result)
    
    ret, result = RoutingServiceApis.UpdateMapping(body['sourceId'], body['nodeTag'])
    if not ret :
        return send_error_message(result)
    
    log_routing_table_update("update", body["sourceId"], body["nodeTag"])
    return send_success_message(result)

@with_logging("/routing/getSourcesByInstance")
@routingService.post("/getSourcesByInstance")
async def getSourcesByInstance(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['framedb'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = RoutingServiceApis.GetSourcesByFramedb(body['framedb'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging("/routing/getSourcesByNode")
@routingService.post("/getSourcesByNode")
async def getSourcesByNode(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['nodeTag'])
    if not ret :
        return send_error_message("Missing field " + field)
    ret, result = RoutingServiceApis.GetSourcesByNode(body['nodeTag'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging("/routing/reassignInstance")
@routingService.post("/reassignInstance")
async def reassignInstance(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['nodeTag', 'framedb'])
    if not ret :
        return send_error_message("Missing field " + field)
    ret, result = RoutingServiceApis.ReassignInstances(body['nodeTag'], body['framedb'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging("/routing/reassignSource")
@routingService.post("/ressignSource")
async def reassignSource(body : dict, request : Request) :
    
    log_request(request, body)

    ret, field = validate_json_fields(body, ['nodeTag', 'sourceId', 'framedb'])
    if not ret :
        return send_error_message("Missing field " + field)
    ret, result = RoutingServiceApis.ReassignSource(body['sourceId'], body['nodeTag'], body['framedb'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/routing/getLeastAssignedInstance")
@routingService.post("/getLeastAssignedInstance")
async def getLeastAssignedInstance(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['nodeTag'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = RoutingServiceApis.GetLeastAssignedInstance(body['nodeTag'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/routing/getMaxAssignedInstance")
@routingService.post("/getMaxAssignedInstance")
async def getMaxAssignedInstance(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['nodeTag'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = RoutingServiceApis.GetMaxAssignedInstance(body['nodeTag'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

    log_request(request, body)

    ret, field = validate_json_fields(body, ['nodeTag'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = RoutingServiceApis.GetMaxAssignedInstance(body['nodeTag'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)


@with_logging("/routing/updateMetadata")
@routingService.post("/updateMetadata")
async def updateMetadata(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['sourceId', 'nodeTag', 'metadata'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = RoutingServiceApis.UpdateMetadata(body['sourceId'], body['nodeTag'], body['metadata'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/routing/getMappingMetadata")
@routingService.post("/getMappingMetadata")
async def GetMappingMetadata(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['sourceId', 'nodeTag'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = RoutingServiceApis.GetMappingMetadata(body['sourceId'], body['nodeTag'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)