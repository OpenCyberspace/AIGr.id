from ..configs import settings
from pymodm import connect
import logging

logging = logging.getLogger("MainLogger")

from .cluster_config import * 
from .basic_config import *

class DBApi :

    @staticmethod
    def connect() :
        connect("{}/{}?authSource=admin".format(
            settings.MONGO_URI,
            settings.DB_NAME
        ))

    @staticmethod
    def GetClusterSpec(cluster_name) :
        
        DBApi.connect()

        try:
            clusterSpec = FramedbClusterInfo.objects.get({"_id" : cluster_name})
            return True, clusterSpec    
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def UpdatePodLists(cluster_name, new_framedb_pod) :

        DBApi.connect()

        try:

            clusterSpec = FramedbClusterInfo.objects.get({"_id" : cluster_name})
            clusterSpec.clusterPods.append(new_framedb_pod)
            clusterSpec.update()

            return True, "ClusterSpec updated"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def CreateBasicConfigEntry(cluster_name, pod_data) :
         
         try:

            for pod in pod_data :

                print(pod.status)

                basicConfig = BaseRedisStructure(
                    framedbId = pod.metadata.name,
                    clusterId = cluster_name,
                    role = 'master',
                    discovery = Discovery(
                        host = pod.status.pod_ip,
                        port = 6379,
                        password = settings.FRAMEDB_PASSWORD,
                        clusterServiceHost = "{}-redis.framedb.svc.cluster.local".format(cluster_name),
                        clusterServicePort = 6379,
                        sentinalPassword = settings.FRAMEDB_PASSWORD,
                        sentinalPort = 26379,
                        sentinalHost = pod.status.pod_ip,
                        sentinalMasterName = "mymaster",
                        hostAddress = pod.status.host_ip
                    ),
                    config = {}
                ) 

                basicConfig.save()
            return True, "Created entry in basicConfig"
             
         except Exception as e:
             logging.error(e)
             return False, str(e)

    @staticmethod
    def RemoveFrameDBs(cluster_name, framedb_pods_delete, framedb_pods_keep) :

        DBApi.connect()

        try:

            print("-----", framedb_pods_delete)

            framedbIds = BaseRedisStructure.objects.raw({"_id" : {"$in" : framedb_pods_delete}}).delete()

            #now remove those entries from ClusterSpec
            clusterSpec = FramedbClusterInfo.objects.get({"_id" : cluster_name})
            clusterSpec.clusterPods = framedb_pods_keep

            clusterSpec.save()

            return True, "Updated DB"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def AddFramedDBs(cluster_name, framedb_pods_list, framedb_new_pods) :

        DBApi.connect()
        
        try:

            ret, result = DBApi.CreateBasicConfigEntry(cluster_name, framedb_pods_list)
            if not ret :
                return False, "Failed updating pods list in cluster config"
            
            #reflect changes in cluster-config
            clusterSpec = FramedbClusterInfo.objects.get({"_id" : cluster_name})
            clusterSpec.clusterPods.extend(framedb_new_pods)

            clusterSpec.save()

            return True, "Updated config"
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def DeleteFramedbDeployment(cluster_name) :

        try:

            #remove cluster basic config
            BaseRedisStructure.objects.raw({"clusterId" :  cluster_name}).delete()
            
            #remove clusterSpec
            clusterSpec = FramedbClusterInfo.objects.get({"_id" : cluster_name})
            clusterSpec.delete()

            return True, "Removed deployment {}".format(cluster_name)

        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def AddClusterToDatabase(cluster_name, node, serviceDetails, podsDetails, metricsEnabled = True) :

        def __get_redis_port(data) :
            for port in data.ports :
                if port.name == "redis" :
                    return port.port 
        

        def __get_sentinel_port(data) :

            for port in data.ports :
                if port.name == "redis-sentinel" :
                    return port.port 
        
        def __get_metrics_svc(data) :

            for svc in data :
                if svc.metadata.name == "{}-redis-metrics".format(cluster_name) :
                    return svc 
            
        
        def __get_redis_service(data) :

            for svc in data :
                if svc.metadata.name == "{}-redis".format(cluster_name) :
                    return svc
        

        DBApi.connect()

        try:

            metricsSvc = __get_metrics_svc(serviceDetails)
            redisSvc = __get_redis_service(serviceDetails)

            #create clusterSpec object
            metrics_port = metricsSvc.spec.ports[0].port 
            redis_port = __get_redis_port(redisSvc.spec)
            sentinel_port = __get_sentinel_port(redisSvc.spec)

            clusterSpec = FramedbClusterInfo(
                cluster_name = cluster_name,
                node_tag = node,
                svc_name = "{}-redis.framedb.svc.cluster.local".format(cluster_name),
                svc_host = redisSvc.spec.cluster_ip,
                metrics_svc = metricsSvc.spec.cluster_ip,
                namespace = "framedb",

                master_port = redis_port,
                sentinel_port = sentinel_port,
                metrics_port = metrics_port,
                clusterPods = [pod.metadata.name for pod in podsDetails]
            )

            clusterSpec.save()

            ret, response = DBApi.CreateBasicConfigEntry(cluster_name, podsDetails)
            if not ret :
                return False, "failed writing to mongodb"
                

            return True, "Saved cluster spec"

        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetClustersByNodeTag(nodeTag) :

        try:

            DBApi.connect()

            clusters = FramedbClusterInfo.objects.raw({"node_tag" : nodeTag}).all()
            formatted_data = []

            for cluster in clusters :
                formatted_data.append({
                    "clusterName" : cluster._id,
                    "svcName" : cluster.svc_name,
                    "svcIp" : cluster.svc_host,
                    "sentinelPort" : cluster.sentinel_port,
                    "masterPort" : cluster.master_port
                })
            
            return True, formatted_data

        except Exception as e:
            logging.error(e)
            return False, str(e)
             