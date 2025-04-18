import pymodm
from ..sentinel_api import SentinelApi
from redis import Redis
from .basic_config import *
import logging

from ...configs import settings

logging = logging.getLogger("MainLogger")

class SentinelConnector :

    @staticmethod
    def GetSentinelConnection(framedb_id) :
        try:
            pymodm.connect("{}/{}?authSource=admin".format(
                settings.MONGO_URI, settings.DB_NAME
            ))
            connection = BaseRedisStructure.objects.get({"_id" : framedb_id})
            if connection :

                #get sentinel details
                discovery = connection.discovery
                sentinelHost = discovery.sentinalHost
                sentinelPort = discovery.sentinalPort

                print(discovery.to_son().to_dict())
                sentinelPassword = discovery.sentinalPassword

                masterName = discovery.sentinalMasterName

                #print(sentinelHost, sentinelPort, sentinelPassword)

                ret, connection = SentinelApi.GetSentinelConnection(
                    sentinelHost, sentinelPort, sentinelPassword
                )

                if not ret :
                    return False, str(connection), ""
                #print(connection, masterName)
                return True, connection, masterName

            return False, "Invalid framedb_id", ""
        except Exception as e:
            logging.error(e)
            return False, str(e), ""
    
    @staticmethod
    def GetClusterConnection(clusterName) :

        try:
            pymodm.connect("{}/{}?authSource=admin".format(
                settings.MONGO_URI, settings.DB_NAME
            ))
            connection = BaseRedisStructure.objects.raw({"clusterId" : clusterName}).first()
            if connection :

                #get sentinel details
                discovery = connection.discovery
                sentinelHost = discovery.clusterServiceHost
                sentinelPort = discovery.sentinalPort

                print(discovery.to_son().to_dict())
                sentinelPassword = discovery.sentinalPassword

                masterName = discovery.sentinalMasterName

                #print(sentinelHost, sentinelPort, sentinelPassword)

                ret, connection = SentinelApi.GetSentinelConnection(
                    sentinelHost, sentinelPort, sentinelPassword
                )

                if not ret :
                    return False, str(connection), ""
                #print(connection, masterName)
                return True, connection, masterName

            return False, "Invalid framedb_id", ""
        except Exception as e:
            logging.error(e)
            return False, str(e), ""
    

    @staticmethod
    def GetRedisConnection(framedb_id) :
        try:
            pymodm.connect("{}/{}?authSource=admin".format(
                settings.MONGO_URI, settings.DB_NAME
            ))
            connection = BaseRedisStructure.objects.get({"_id" : framedb_id})
            if connection :

                #get sentinel details
                discovery = connection.discovery
                sentinelHost = discovery.sentinalHost
                sentinelPort = discovery.sentinalPort

                #print(discovery.to_son().to_dict())
                sentinelPassword = discovery.sentinalPassword

                masterName = discovery.sentinalMasterName

                #print(sentinelHost, sentinelPort, sentinelPassword)

                connection = Redis(
                    sentinelHost, sentinelPort, password = sentinelPassword
                )

                #print(connection)
                #print(connection, masterName)
                return True, connection, masterName

            return False, "Invalid framedb_id", ""
        except Exception as e:
            raise e
            return False, str(e), ""