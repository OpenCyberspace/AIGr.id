from fastapi import APIRouter, Request
import yaml
import logging
import requests
import time
logging = logging.getLogger("MainLogger")

from .k8s_api import K8sApi
from .db.db_api import DBApi
from .configs import settings

from .exec.helm_executor import HelmSubprocessApi
from .utils import validate_json_fields, send_error_message, send_success_message, with_logging

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


def update_state_to_routing_service(clusterName, nodeTag) :

    try:

        routing_uri = settings.ROUTING_REASSIGN_API
        payload = {"framedb" : clusterName, "nodeTag" : nodeTag}

        response = requests.post(routing_uri, json = payload)
        
    except Exception as e:
        logging.error(e)



class FramedbClusterManager :

    @staticmethod
    def RemoveCluster(cluster_name) :

        ret, clusterSpec = DBApi.GetClusterSpec(cluster_name)
        if not ret :
            return False, "Cluster {} does not exist".format(cluster_name)
        
        namespace = clusterSpec.namespace

        HelmSubprocessApi.RemoveDeployment(cluster_name, namespace)

        #delete entries from database
        ret, result = DBApi.DeleteFramedbDeployment(cluster_name)
        if not ret :
            return False, "Cluster deleted, but not removed from database"
        
        update_state_to_routing_service(cluster_name, clusterSpec.node_tag)
        
        return True, "Deleted cluster"
    
    @staticmethod
    def GetClusterInfo(cluster_name) :

        ret, clusterSpec = DBApi.GetClusterSpec(cluster_name)
        if not ret :
            return False, "Cluster {} does not exist".format(cluster_name)
        return True, clusterSpec.to_son().to_dict()
    

    @staticmethod
    def CheckSvcGotIp(svc_data, releaseName) :

        for svc in svc_data :
            if svc.metadata.name == "{}-redis-headless".format(releaseName) :
                continue
            if not svc.spec.cluster_ip :
                return False
        return True
    
    @staticmethod
    def PodsGotIp(pod_data) :

        for pod in pod_data :
            if (not pod.status.pod_ip) or (not pod.status.host_ip):
                return False

        return True

    @staticmethod
    def CreateCluster(clusterName, nodeTag, replicas, enableMetrics = True, quorum = 1, failoverTimeout = 18000, downAfterMilliseconds = 60000) :

        if replicas == 0 :
            return False, "Zero deployments not allowed"
        
        #check if cluster already exists:
        ret, result = FramedbClusterManager.GetClusterInfo(clusterName)
        if ret :
            return False, "Cluster already exists!"
        
        #read yaml
        try:
            production_values = yaml.load(open('values/values-production.yaml', 'r'))

            #assign node-labels :
            production_values['master']['nodeSelector']['framedb'] = nodeTag
            production_values['slave']['nodeSelector']['framedb'] = nodeTag

            #slave count/replicas
            production_values['cluster']['slaveCount'] = replicas

            #sentinel quorum
            production_values['sentinel']['quorum'] = quorum

            #set deployment password
            production_values['password'] = settings.FRAMEDB_PASSWORD

            #enable/disable metrics
            production_values['metrics']['enabled'] = enableMetrics

            dumpFile = '/tmp/{}.yaml'.format(clusterName)
            yaml.dump(production_values , open(dumpFile, 'w'))

            #call helm creator
            # HelmSubprocessApi.ExecuteHelmAddRepo()
            HelmSubprocessApi.DeployFramedbWithHelm(
                clusterName, dumpFile
            )

            svcData = []
            coreK8Client = K8sApi.GetK8sCoreApi()
            while True :
                svcData = K8sApi.GetServicesByStatefulSet(coreK8Client, clusterName, "framedb")
                if (len(svcData) < 2) or ( not FramedbClusterManager.CheckSvcGotIp(svcData, clusterName)) :
                    time.sleep(2)
                    continue
                else :
                    break

            #get pods
            pods = []
            while True :
                pods = K8sApi.GetPodsByStatefulSet(coreK8Client, clusterName, "framedb")
                if ( len(pods) != replicas ) or (not FramedbClusterManager.PodsGotIp(pods)) :
                    time.sleep(2)
                    continue
                else :
                    break

            #populate data to database
            ret, dbResult = DBApi.AddClusterToDatabase(clusterName, nodeTag, svcData, pods)
            if not ret :
                return False, "Writing to db failed"
            
            return True, "Cluster created"

            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    def GetFramedbDeployments(synchronize : bool = False) :

        try:

            k8Client = K8sApi.GetK8sCoreApi()
            svcData = K8sApi.GetSvcByNamespace(k8Client, "framedb")

            #get labels of the services - as they represent cluster names :
            framedbClusters = []
            for svc in svcData :
                clusterName = svc.metadata.labels['release']
                if clusterName not in framedbClusters :
                    framedbClusters.append(clusterName)
            

            if synchronize :
                for cluster in framedbClusters :
                    ret, result = FramedbClusterManager.SynchronizeDBWithCluster(cluster)
                    if not ret :
                        logging.error('Failed cluster synchronization')
                        return False,  'Failed cluster synchronization'
                
            
            return True, framedbClusters
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    def SynchronizeDBWithCluster(clusterName : str) :
        
        try:

            #get services :
            k8Client = K8sApi.GetK8sCoreApi()
            svcData = K8sApi.GetServicesByStatefulSet(k8Client, clusterName, "framedb")

            #get pods :
            pods = K8sApi.GetPodsByStatefulSet(k8Client, clusterName, "framedb")

            #get node tag from the one of the pods :
            if len(pods) == 0 or len(svcData) == 0 :
                return True, "Nothing to synchronize"
            
            #print(pods[0].spec)
            nodeTag = pods[0].spec.node_selector['framedb'] 


            ret, dbResult = DBApi.AddClusterToDatabase(clusterName, nodeTag, svcData, pods)
            if not ret :
                return False, "Failed to Sync with DB data"
            
            return True, "Synchronized with database" 
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def DeployClustersMulti(clusterSuffix, nClusters, start_index , nodeTag, replicas, enableMetrics = True, quorum = 1, failoverTimeout = 18000, downAfterMilliseconds = 60000) :

        for i in range(nClusters) :
            index_number = start_index + i
            clusterName = clusterSuffix + "-{}".format(index_number)

            ret, result = FramedbClusterManager.CreateCluster(
                clusterName, nodeTag, replicas, enableMetrics, quorum,
                failoverTimeout, downAfterMilliseconds
            )

            if not ret :
                print('Creating cluster failed for {} because : '.format(clusterName, result))
        
        return True, "Created {} clusters.".format(nClusters)
    
    @staticmethod
    def RemoveMultiClusters(clusterNames) :

        failed_removals = []
        nClusters = 0
        for clusterName in clusterNames :
            ret, result = FramedbClusterManager.RemoveCluster(
                clusterName
            )

            if not ret :
                failed_removals.append(clusterName)
            else :
                nClusters +=1
        
        return True, {"nClustersRemoved" : nClusters, "failedRemovals" : failed_removals}


clusterRouter = APIRouter()


@with_logging("/cluster/removeCluster")
@clusterRouter.post("/removeCluster")
async def removeCluster(body: dict, request : Request) :

    log_request(request, body)
    
    ret, fields = validate_json_fields(body, ['clusterName'])
    if not ret :
        return send_error_message("Missing field " + fields)
    
    ret, result = FramedbClusterManager.RemoveCluster(body['clusterName'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/cluster/getClusterInfo")
@clusterRouter.post("/getClusterInfo")
async def getClusterInfo(body : dict, request : Request) :

    log_request(request, body)

    ret, fields = validate_json_fields(body, ['clusterName'])
    if not ret :
        return send_error_message("Missing field " + fields)
    
    ret, result = FramedbClusterManager.GetClusterInfo(body['clusterName'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging("/cluster/createCluster")
@clusterRouter.post("/createCluster")
async def createCluster(body : dict, request : Request) :

    log_request(request, body)

    ret, fields = validate_json_fields(body, ['clusterName', 'nodeTag', 'replicas', 'enableMetrics', 'quorum'])
    if not ret :
        return send_error_message("Missing field " + fields)
    
    ret, result = FramedbClusterManager.CreateCluster(
        body['clusterName'], body['nodeTag'], body['replicas'], body['enableMetrics'],
        body['quorum']
    )

    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)



@with_logging("/cluster/synchronize")
@clusterRouter.post("/synchronize")
async def synchronize(body : dict, request : Request) :

    log_request(request, body)

    ret, fields = validate_json_fields(body, ['synchronize'])
    if not ret :
        return send_error_message("Missing field " + fields)
    
    ret, result = FramedbClusterManager.GetFramedbDeployments(body['synchronize'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/cluster/synchronizeCluster")
@clusterRouter.post("/synchronizeCluster")
async def synchronizeCluster(body : dict, request : Request) :

    log_request(request, body)

    ret, fields = validate_json_fields(body, ['clusterName'])
    if not ret :
        return send_error_message("Missing field " + fields)
    
    ret, result = FramedbClusterManager.SynchronizeDBWithCluster(body['clusterName'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/cluster/createClusters")
@clusterRouter.post("/createClusters")
async def createClusters(body : dict, request : Request) :

    log_request(request, body)
    ret, field = validate_json_fields(body, ['clusterPrefix', 'startIndex', 'nClusters', 'nodeTag', 'replicas', 'enableMetrics', 'quorum'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = FramedbClusterManager.DeployClustersMulti(
        body['clusterPrefix'], body['nClusters'], body['startIndex'],
        body['nodeTag'], body['replicas'], body['enableMetrics'],
        body['quorum']
    )

    if not ret :
        return send_success_message(result)
    return send_success_message(result)

@with_logging("/cluster/removeClusters")
@clusterRouter.post("/removeClusters")
async def removeClusters(body : dict, request : Request) :
    log_request(request, body)
    ret, fields = validate_json_fields(body, ['clusterList'])
    if not ret :
        return send_error_message("Missing field " + fields)
    
    ret, result = FramedbClusterManager.RemoveMultiClusters(body['clusterList'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)