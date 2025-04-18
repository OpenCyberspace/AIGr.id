from .k8s_api import K8sApi
from .db.db_api import DBApi
from .utils import with_logging, validate_json_fields, send_success_message, send_error_message

import logging
from fastapi import APIRouter, Request
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

class NodesController :

    @staticmethod
    def GetNodes() :

        def GetNodeAddress(node : str) :
            for address in node.status.addresses :
                if address.type == 'InternalIP' :
                    return address.address
        
        def GetNodeHostname(node : str) :

            for address in node.status.addresses :
                if address.type == "Hostname" :
                    return address.address
        
        try :
        
            k8Client = K8sApi.GetK8sCoreApi()
            nodeData = K8sApi.GetNodes(k8Client)

            nodes = []
            for node in nodeData :
                nodes.append(
                    {
                        "labels" : node.metadata.labels,
                        "node_info" : node.status.node_info,
                        "ipv4Address" : GetNodeAddress(node),
                        "hostname" : GetNodeHostname(node),
                        "name" : node.metadata.name
                    }
                )
        
            return True, nodes
        except Exception as e :
            logging.error(e)
            return False, str(e)


    
    @staticmethod
    def EnableFramedForNode(nodeName : str, framedbName : str) :
        
        try:

            k8Client = K8sApi.GetK8sCoreApi()
            response = K8sApi.LabelNode(
                k8Client,
                nodeName,
                "framedb",
                framedbName
            )

            return True, response
            
        except Exception as e:
            logging.error(e)
            return False, str(e)

    
    @staticmethod
    def DisableFramedbForNode(nodeName : str) :

        try:

            k8Client = K8sApi.GetK8sCoreApi()
            response = K8sApi.LabelNode(
                k8Client,
                nodeName,
                "framedb",
                None
            )

            return True, response
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetFramedbPodsByNode(nodeName : str) :

        try:
            client = K8sApi.GetK8sCoreApi()
            nodePods = K8sApi.GetNamespacedPodsByNode(client, nodeName, "framedb")
            
            formattedData = []
            #format the data:
            for pod in nodePods :
                formattedData.append({
                    "pod_name" : pod.metadata.name,
                    "ip" : pod.status.pod_ip
                })
            
            return True, formattedData
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetFramedbNodes(nodeTag : str) :

        try:

            ret, results = DBApi.GetClustersByNodeTag(nodeTag)
            if not ret :
                return False, results
            
            return True, results
            
        except Exception as e:
            logging.error(e)
            return False, str(e)

nodesRouter = APIRouter()

@with_logging("/nodes/getNodes")
@nodesRouter.get("/getNodes")
async def getNodes(request : Request) :
    log_request(request)
    ret, result = NodesController.GetNodes()
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/nodes/labelFramedbNode")
@nodesRouter.post("/labelFramedbNode")
async def labelNode(body : dict, request : Request) :

    log_request(request, body)

    ret, result = validate_json_fields(body, ['nodeName', 'framedbName'])
    if not ret :
        return send_error_message("Missing field " + result)

    ret, result = NodesController.EnableFramedForNode(body['nodeName'], body['framedbName'])
    if not ret :
        return send_error_message(result)

    return send_success_message(result) 

@with_logging("/nodes/unlabelFramedbNode")
@nodesRouter.post("/unlabelFramedbNode")
async def labelNode(body: dict, request : Request) :

    log_request(request, body)

    ret, result = validate_json_fields(body, ['nodeName'])
    if not ret :
        return send_error_message("Missing field " + result)

    ret, result = NodesController.DisableFramedbForNode(body['nodeName'])
    if not ret :
        return send_error_message(result)

    return send_success_message(result) 


@with_logging("/nodes/getFramedbPods")
@nodesRouter.post("/getFramedbPods")
async def getFramedbPods(body : dict, request : Request) :

    log_request(request, body)

    ret, result = validate_json_fields(body, ['nodeName'])
    if not ret :
        return send_error_message("Missing field " + result)
    
    ret, result = NodesController.GetFramedbPodsByNode(body['nodeName'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/nodes/getFramedbNodes")
@nodesRouter.post("/getFramedbNodes")
async def getFramedbNodes(body : dict, request : Request) :

    log_request(request, body)

    ret, result = validate_json_fields(body, ['nodeTag'])
    if not ret :
        return send_error_message("Missing field " + result)
    
    ret, result = NodesController.GetFramedbNodes(body['nodeTag'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)