from fastapi import APIRouter, Request
from .update import PubSubUpdater
from .db.db_api import FramedbToSourceApi
from .utils import validate_json_fields, send_error_message, send_success_message, with_logging
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

class BackPreassureController :

    @staticmethod
    def HandleNodeWrites(sourceId, nodeTag, enabled) :

        try :

            result = None
            ret = None

            if enabled :
                ret, result = PubSubUpdater.GenericPublish(
                    sourceId, "bp_on", {"nodeTag" : nodeTag}
                )
            else :
                ret, result = PubSubUpdater.GenericPublish(
                    sourceId, "bp_off", {"nodeTag" : nodeTag}
                )
        
            if not ret :
                logging.error(result)
                return False, str(result)
        
            return True, "Published updates"

        except Exception as e :
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def BackPressureNode(nodeTag, enabled = False) :

        try :

            ret, nodeData = FramedbToSourceApi.GetSourcesWritingByNode(nodeData)
            if not ret :
                return False, "Failed to query db"
        
            src_set = set()
            instances = nodeData['framedbInstances']
            for instance in instances :
                sources = instances[instance]['sources']
                for source in sources :
                    src_set.add(source)
        
            ret = False
            result = None

            print('sources : ', src_set)
        
            #publish
            if enabled :

                ret, result = PubSubUpdater.GenericMultiPublish(
                    list(src_set),
                    "bp_on",
                    {"nodeTag" : nodeTag}
                )
            else :
                ret, result = PubSubUpdater.GenericMultiPublish(
                    list(src_set),
                    "bp_off",
                    {"nodeTag" : nodeTag}
                )
        
            if not ret :
                logging.error(result)
                return False, "Failed to push pub-sub updates"
        
            return True, "Pushed pub-sub updates"

        except Exception as e :
            logging.error(e)
            return False, str(e)



    @staticmethod
    def BackPressureInstance(framedb, enabled = False) :
        
        try:

            ret, instanceData = FramedbToSourceApi.GetSourcesWritingByDb(
                framedb
            )

            if not ret :
                return False, "failed to fetch instance data"
            
            #get sources list 
            sources = instanceData['sources']

            ret = False
            result = None
            
            if enabled :
                ret, result = PubSubUpdater.GenericMultiPublish(
                    sources, 
                    "bp_on", 
                    {"nodeTag" : instanceData['nodeTag'], "cluster_name" : framedb}
                )
            else :

                ret, result = PubSubUpdater.GenericMultiPublish(
                    sources,
                    "bp_off",
                    {"nodeTag" : instanceData['nodeTag'], "cluster_name" : framedb}
                )
            
            if not ret :
                logging.error("Failed to publish pub-sub updates")
                return False, "Failed to publish pub-sub updates"
            
            return True, "Published pub-sub updates"

        except Exception as e:
            logging.error(e)
            return False, str(e)

    
    @staticmethod
    def HandleSourceWrites(sourceId, enabled) :

        try :

            result = None 
            ret = None 

            if enabled :
                ret, result = PubSubUpdater.GenericPublish(
                    sourceId, "bp_source_on", {"sourceId" : sourceId}
                )
            else :
                ret, result = PubSubUpdater.GenericPublish(
                    sourceId, "bp_source_off", {"sourceId" : sourceId}
                )
        
            if not ret :
                logging.error(result)
                return False, str(result)
        
            return True, "Published updates"

        except Exception as e :
            logging.error(e)
            return False, str(e)


backpreassureRouter = APIRouter()

@with_logging("/backpressure/enable")
@backpreassureRouter.post("/enable")
async def enableBackpreassure(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['sourceId'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    if 'nodeTag' in body :
        ret, result = BackPreassureController.HandleNodeWrites(body['sourceId'], body['nodeTag'], True)
        if not ret :
            return send_success_message(result)
        return send_success_message(result)
    else :
        ret, result = BackPreassureController.HandleSourceWrites(body['sourceId'], True)
        if not ret :
            return send_error_message(result)
        return send_success_message(result)

@with_logging("/backpressure/disable")
@backpreassureRouter.post("/disable")
async def enableBackpreassure(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['sourceId'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    if 'nodeTag' in body :
        ret, result = BackPreassureController.HandleNodeWrites(body['sourceId'], body['nodeTag'], False)
        if not ret :
            return send_success_message(result)
        return send_success_message(result)
    else :
        ret, result = BackPreassureController.HandleSourceWrites(body['sourceId'], False)
        if not ret :
            return send_error_message(result)
        return send_success_message(result)

@with_logging("/backpressure/nodeEnable")
@backpreassureRouter.post("/nodeEnable")
async def enableBackpreassure(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['nodeTag'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = BackPreassureController.BackPressureNode(body['nodeTag'], enabled = True)
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging("/backpressure/nodeDisable")
@backpreassureRouter.post("/nodeDisable")
async def enableBackpreassure(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['nodeTag'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = BackPreassureController.BackPressureNode(body['nodeTag'], enabled = False)
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging("/backpressure/instanceEnable")
@backpreassureRouter.post("/instanceEnable")
async def enableBackpreassure(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, ['framedb'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = BackPreassureController.BackPressureInstance(body['nodeTag'], enabled = True)
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging("/backpressure/instanceDisable")
@backpreassureRouter.post("/instanceDisable")
async def enableBackpreassure(body : dict, request : Request) :

    log_request(request, body)

    ret, field = validate_json_fields(body, [''])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = BackPreassureController.BackPressureInstance(body['nodeTag'], enabled = False)
    if not ret :
        return send_error_message(result)
    return send_success_message(result)