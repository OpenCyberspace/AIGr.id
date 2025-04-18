from redis import sentinel
import random
import logging


logging = logging.getLogger("MainLogger")

from .db_api import FramedbConfigAPI, MappingDBApi, FramedbToSourceApi
from ..configs import settings


class SentinelMasterDiscovery :

    @staticmethod
    def DiscoverMaster(nodeTag) :

        try:

            ret, framedbObjects = FramedbConfigAPI.GetFramedbNodes(nodeTag)
            if not ret :
                return False, "Failed to get data from DB", None

            if len(framedbObjects) == 0 :
                return False, "No framedb deployments in node {}".format(nodeTag), None
            

            ret, sortedInstances = FramedbToSourceApi.GetNodes(nodeTag)
            if not ret :
                return False, "Communication with metadata db failed"
            
            framedbInstance = None 
            if len(sortedInstances) == 0 :
                ret, result = FramedbToSourceApi.InsertInstancesInitial(framedbObjects, nodeTag)
                if not ret :
                    return False, "Failed to update database"
                
                framedbInstance = random.choice(framedbObjects)
                logging.info("Selected {} randomly".format(framedbInstance.cluster_name))
            
            else :

                print(len(sortedInstances), len(framedbObjects))

                if len(sortedInstances) < len(framedbObjects) :
                    sortedInstanceNames = [sortedInstance.framedb for sortedInstance in sortedInstances]

                    #update table with new instances :
                    new_instances = [framedbObject for framedbObject in framedbObjects if framedbObject.cluster_name not in sortedInstanceNames]
                    #update new instances:
                    ret, result = FramedbToSourceApi.InsertInstancesInitial(new_instances, nodeTag)
                    if not result :
                        logging.error(result)
                        return False, "Failed to update db state"
                    
                elif len(sortedInstances) > len(framedbObjects):

                    framedbClusterNames = [instance.cluster_name for instance in framedbObjects]

                    to_remove_instances = [sortedInstance.framedb for sortedInstance in sortedInstances if sortedInstance.framedb not in framedbClusterNames]

                    #update db 
                    ret, result = FramedbToSourceApi.RemoveEntries(to_remove_instances)
                    if not ret :
                        logging.error(result)
                        return False, "Failed to update DB"

                else :
                    logging.info("routing table data is in sync with cluster")

                leastAllocatedInstance = sortedInstances[-1].framedb
                for instance in framedbObjects :
                    if instance.cluster_name == leastAllocatedInstance :
                        framedbInstance = instance   
                
                logging.info("Selected {} as the least allocated instance".format(framedbInstance.cluster_name))

            svcHost = framedbInstance.svc_name
            svcPort = framedbInstance.sentinel_port

            master = None 

            if not settings.LOCAL_MODE :
                sentinelConnection = sentinel.Sentinel([(svcHost, svcPort)], sentinel_kwargs = {"password" : "Friends123#"})
                master = sentinelConnection.discover_master("mymaster")
            
            else :
                master = ("localhost", 6379)

            if len(master) == 0:
                return False, "Failed to discover master, maybe the cluster doesnt have a master" 
            
            #save master cluster :
            masterIp = master[0]
            return True, framedbInstance, masterIp
            
        except Exception as e:
            logging.error(e)
            return False, str(e), ""
    
    @staticmethod
    def RediscoverMaster(sourceId, nodeTag) :

        try:

            ret, mapping = MappingDBApi.GetMappingSourceAsObject(sourceId)
            if not ret :
                return False, "No mapping entry for {}".format(sourceId)

            #get object with node tag:
            nodeObject = [(node, index) for index, node in enumerate(mapping.framedbNodes) if node.nodeTag == nodeTag]
            nodeObject, indexOfNode = nodeObject[0]

            #run discovery :
            svc_host = nodeObject.serviceIp
            svc_port = nodeObject.sentinelPort 

            master = None 
            if not settings.LOCAL_MODE :
                sentinelConnection = sentinel.Sentinel([(svc_host, svc_port)], sentinel_kwargs = {"password" : "Friends123#"})
                master = sentinelConnection.discover_master("mymaster")
            else :
                master = ("localhost", 6379)
            
            if len(master) == 0 :
                logging.error("No masters found for {}".format(nodeTag)), "", ""
            
            # update the new master to the database
            master = master[0]

            mapping.framedbNodes[indexOfNode].masterIp = master
            mapping.save()

            logging.info("Updated mapping table")

            nodeObject.masterIp = master
            
            return True, nodeObject
            
        except Exception as e:
            logging.error(e)
            return False, str(e)


    
    