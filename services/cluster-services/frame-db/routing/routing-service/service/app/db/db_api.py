from ..configs import settings
from .source_mapping import *
from .framedb_mapping import *
from .cluster_config import *

import redis
import pymodm
import logging

logging = logging.getLogger("MainLogger")

class MappingDBApi :

    @staticmethod
    def connect_framedb_config() :
        logging.info("Connected to DB")
        pymodm.connect("{}/{}?authSource=admin".format(
            settings.FRAMEBD_CONFIG_URI, settings.DB_NAME
        ))
    
    @staticmethod
    def connect_mapping_config() :
        logging.info("Connected to DB")
        pymodm.connect("{}/{}?authSource=admin".format(
            settings.FRAMEDB_MAPPING_URI, settings.DB_NAME
        ))
    
    @staticmethod
    def GetMappingMetadata(sourceId, nodeTag) :

        try:
            MappingDBApi.connect_mapping_config()
            #get sources by sourceId

            sourceMapping = FrameSourceMapping.objects.get({"_id" : sourceId})
            
            nodes = sourceMapping.framedbNodes

            for node in nodes :
                if node.nodeTag == nodeTag :
                    return True, node.metadata 
            
            return False, "Source {} not writing to {}".format(sourceId, nodeTag)
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetMappingForSource(sourceId) :
        try:
            MappingDBApi.connect_mapping_config()
            #get sources by sourceId 
            result = FrameSourceMapping.objects.get({"_id" : sourceId})

            #return formatted data :
            formatted_data = {
                "sourceId" : sourceId,
                "nodeTags" : result.nodeTags,
                "framedbNodes" : [node.to_son().to_dict() for node in result.framedbNodes]
            }

            return True, formatted_data

        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetMappingSourceAsObject(sourceId) :

        try:

            MappingDBApi.connect_mapping_config()

            result = FrameSourceMapping.objects.get({"_id" : sourceId})
            return True, result            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def CreateNewMapping(sourceId, framedbNodeData, nodeTag, masterIP, metadata = None) :

        try:

            MappingDBApi.connect_mapping_config()

            framedbNodeObject = Framedb(
                serviceIp = framedbNodeData.svc_host,
                sentinelPort = framedbNodeData.sentinel_port,
                serviceName = framedbNodeData.svc_name,
                redisPort = framedbNodeData.master_port,
                masterIP = masterIP,
                nodeTag = nodeTag,
                cluster_name = framedbNodeData.cluster_name,
                metadata = metadata if metadata else {"empty" : True}
            )

            mappingObject = [fdb for fdb in FrameSourceMapping.objects.raw({"_id" : sourceId})]
            if len(mappingObject) == 0 :
                #create a new mapping object
                
                mappingObject = FrameSourceMapping(
                    sourceId = sourceId,
                    nodeTags = [nodeTag],
                    framedbNodes = [framedbNodeObject]
                )

                mappingObject.save()

            else :

                mappingObject = mappingObject[0]
                if nodeTag in mappingObject.nodeTags :
                    return False, "Mapping already exist, no need to update"

                framedbNodes = mappingObject.framedbNodes
                framedbNodes.append(framedbNodeObject)
                mappingObject.framedbNodes = framedbNodes

                mappingObject.nodeTags.append(nodeTag)

                mappingObject.save()
            
            return True, "Mapping table updated for " + sourceId
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def OverrideNewInstances(sourceIds, framedbNodeData, masterIP, nodeTag) :

        try:

            framedbObject = Framedb(
                serviceIp = framedbNodeData.svc_host,
                sentinelPort = framedbNodeData.sentinel_port,
                serviceName = framedbNodeData.svc_name,
                redisPort = framedbNodeData.master_port,
                masterIP = masterIP,
                nodeTag = nodeTag,
                cluster_name = framedbNodeData.cluster_name,
                metadata = {"empty" : True}
            )

            MappingDBApi.connect_mapping_config()
            for sourceId in sourceIds :

                mappingObject = FrameSourceMapping.objects.get({"_id" : sourceId})
                
                #update the source
                nodeIndex = 0
                for idx, instance in enumerate(mappingObject.framedbNodes) :
                    if instance.nodeTag == nodeTag :
                        nodeIndex = idx 
                        break
                
                #update index :

                #retain old metadata
                framedbObject.metadata = mappingObject.framedbNodes[nodeIndex].metadata

                mappingObject.framedbNodes[nodeIndex] = framedbObject
                mappingObject.save()
            
            return True, "Updated nodes"

            
        except Exception as e:
            logging.error(e)
            return False, str(e)

    @staticmethod
    def RemoveMapping(sourceId, nodeTag) :

        try:
            MappingDBApi.connect_mapping_config()
            mappingObject = FrameSourceMapping.objects.get({"_id" : sourceId})
            if mappingObject :
                #check if nodeTag exists:
                if nodeTag not in mappingObject.nodeTags :
                    return False, "{} is not writing to {}".format(sourceId, nodeTag), None
                
                mappingObject.nodeTags.remove(nodeTag)

                #delete the framedb object
                framedbNodes = mappingObject.framedbNodes
                framedbNodes = [framedbNode for framedbNode in framedbNodes if framedbNode.nodeTag != nodeTag]

                framedbNodeToBeRemoved = [framedbNode for framedbNode in mappingObject.framedbNodes if framedbNode.nodeTag == nodeTag]
                framedbNodeToBeRemoved = framedbNodeToBeRemoved[0]

                mappingObject.framedbNodes = framedbNodes

                if len(mappingObject.nodeTags) == 0 or len(mappingObject.framedbNodes) == 0:
                    mappingObject.delete()
                
                else :
                    mappingObject.save()

            return True, "Updated mapping entry for " + sourceId, framedbNodeToBeRemoved.cluster_name
                
        except Exception as e:
            logging.error(e)
            return False, str(e), None
    

    @staticmethod
    def UpdateMappingInfo(sourceId, framedbNodeData, nodeTag, masterIP) :

        try:

            MappingDBApi.connect_mapping_config()
            mappingObject = FrameSourceMapping.objects.get({"_id" : sourceId})

            if nodeTag not in mappingObject.nodeTag :
                return False, "Mapping between {} and {} does not exist to update".format(sourceId, nodeTag)
            
            nodes = mappingObject.framedbNodes

            #nodes = [node for node in nodes if node.nodeTag != nodeTag]
            nodeIndex = None
            for idx, node in enumerate(nodes) :
                if node.nodeTag == nodeTag :
                    nodeIndex = idx 
            

            #retain metadata while updating
            
            framedbNodeObject = Framedb(
                serviceIp = framedbNodeData.svc_host,
                sentinelPort = framedbNodeData.sentinel_port,
                serviceName = framedbNodeData.svc_name,
                redisPort = framedbNodeData.master_port,
                masterIP = masterIP,
                nodeTag = nodeTag,
                cluster_name = framedbNodeData.cluster_name,
                metadata = nodes[nodeIndex].metadata
            )

            nodes[index] = framedbNodeObject

            #framedbNodeObject = Framedb(
            #    serviceIp = framedbNodeData.svc_host,
            #    sentinelPort = framedbNodeData.sentinel_port,
            #    serviceName = framedbNodeData.svc_name,
            #    redisPort = framedbNodeData.master_port,
            #    masterIP = masterIP,
            #    nodeTag = nodeTag,
            #    cluster_name = framedbNodeData.cluster_name
            #)

            #nodes.append(framedbNodeObject)

            mappingObject.framedbNodes = nodes

            mappingObject.save()

            return True, "Updated mapping table"

            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def UpdateMetadata(sourceId, nodeTag, metadata = {}) :

        try:

            MappingDBApi.connect_mapping_config()
            sourceMappingData = FrameSourceMapping.objects.get({"_id" : sourceId})

            for idx in range(len(sourceMappingData.framedbNodes)) :
                if sourceMappingData.framedbNodes[idx].nodeTag == nodeTag :
                    sourceMappingData.framedbNodes[idx].metadata = metadata
                    break
            
            else :
                return False, "{} not writing to node {}.".format(sourceId, nodeTag)
            
            sourceMappingData.save()
            return True, "Metadata updated."
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

class FramedbConfigAPI :

    @staticmethod
    def connect_framedb_config() :
        logging.info("Connected to DB")
        pymodm.connect("{}/{}?authSource=admin".format(
            settings.FRAMEBD_CONFIG_URI, settings.DB_NAME
        ))

    @staticmethod
    def GetFramedbNodes(nodeTag) :

        try:
            FramedbConfigAPI.connect_framedb_config()
            framedbObjects = FramedbClusterInfo.objects.raw({"node_tag" : nodeTag}).all()
            return True, [framedbObject for framedbObject in framedbObjects]
            
        except Exception as e:
            logging.error(e)
            return False, str(e)

class FramedbToSourceApi :

    @staticmethod
    def connect_mapping_config() :
        logging.info("Connected to DB")
        pymodm.connect("{}/{}?authSource=admin".format(
            settings.FRAMEDB_MAPPING_URI, settings.DB_NAME
        ))
    
    @staticmethod
    def GetSourcesWritingByDb(framedbId) :

        try:
            FramedbToSourceApi.connect_mapping_config()

            framedbData = FramedbToSource.objects.get({"_id" : framedbId})
            return True, framedbData.to_son().to_dict()

        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetSourcesWritingByNode(nodeTag) :

        try:

            FramedbToSourceApi.connect_mapping_config()

            framedbNodes = FramedbToSource.objects.raw({"nodeTag" : nodeTag}).all()

            formatted_dict = {}

            for framedbNode in framedbNodes :
                formatted_dict[framedbNode.framedb] = framedbNode.to_son().to_dict()
            
            return True, {"nodeTag" : nodeTag, "framedbInstances" : formatted_dict}
                
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def AddEntry(framedb, source, nodeTag) :

        try:

            FramedbToSourceApi.connect_mapping_config()
            
            mappingObject = FramedbToSource.objects.get({"_id" : framedb})
            
            if source in mappingObject.sources :
                return True, "Source already in the mapping"
            
            mappingObject.sources.append(source)
            mappingObject.sourceCount +=1
            mappingObject.save()

            return True, "Saved to database"


        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def RemoveEntry(framedb, source, nodeTag) :

        print(framedb, source, nodeTag)

        try:
            FramedbToSourceApi.connect_mapping_config()
            framedbObject = FramedbToSource.objects.get({"_id" : framedb})
            
            #remove source 
            framedbObject.sources = [source for source in framedbObject.sources if source != source]
            
            if framedbObject.sourceCount > 0 :
                framedbObject.sourceCount -=1
            
            framedbObject.save()

            return True, "Source removed"

        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def GetNodes(nodeTag) :

        try:
            FramedbToSourceApi.connect_mapping_config()
            nodes =  [obj for obj in FramedbToSource.objects.raw({ "$query" : {"nodeTag" : nodeTag}, "$orderby" : {"sourceCount" : -1} })]
            return True, nodes

        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def InsertInstancesInitial(framedbObjects, nodeTag) :

        try:

            FramedbToSourceApi.connect_mapping_config()

            for obj in framedbObjects :
                mappingObject = FramedbToSource(
                    framedb = obj.cluster_name,
                    sources = [],
                    nodeTag = nodeTag,
                    sourceCount = 0
                )

                mappingObject.save()
            
            return True, "initialized entries"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def AddEntries(framedb, sourcesList) :

        try:
            FramedbToSourceApi.connect_mapping_config()

            framedbObject = FramedbToSource.objects.get({"_id" : framedb})
            framedbObject.sources.extend(sourcesList)
            framedbObject.sourceCount += len(sourcesList)

            framedbObject.save()

            return True, "Updated entries"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def RemoveEntries(entry_list) :

        try:

            FramedbToSourceApi.connect_mapping_config()
            FramedbToSource.objects.raw({"_id" : { "$in" : entry_list }}).delete()
            return True, "Removed objects"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetSourcesAndRemove(framedb) :

        try:

            FramedbToSourceApi.connect_mapping_config()
            framedbObject = FramedbToSource.objects.get({"_id" : framedb})

            sources = framedbObject.sources 
            framedbObject.delete()

            return True, sources
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetLeastAssignedInstance(nodeTag) :

        try:

            FramedbToSourceApi.connect_mapping_config()
            framedbObject = [fdb for fdb in FramedbToSource.objects.raw({"$query" : {"nodeTag" : nodeTag}, "$orderby" : {"sourceCount" : -1}})]
            
            if len(framedbObject) == 0 :
                return False, "No nodes assigned yet"
            
            return True, framedbObject[-1].to_son().to_dict()
             
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetMaxAssignedInstance(nodeTag) :

        try:

            FramedbToSourceApi.connect_mapping_config()
            framedbObject = [fdb for fdb in FramedbToSource.objects.raw({"$query" : {"nodeTag" : nodeTag}, "$orderby" : {"sourceCount" : 1}})]
            
            if len(framedbObject) == 0 :
                return False, "No nodes assigned yet"
            
            return True, framedbObject[-1].to_son().to_dict()
             
        except Exception as e:
            logging.error(e)
            return False, str(e)