from redis import Redis, sentinel
from .configs import settings

import json
import logging
logging = logging.getLogger("MainLogger")

ROUTING_PUBSUB = "routing_updates"

def log_publish(sourceId, command, receivers) :

    logging.info("Published routing table update", extra = {
        "sourceId" : sourceId,
        "command" : command,
        "receiverCount" :  receivers
    })

class PubSubUpdater :

    @staticmethod
    def GetConnection() :

        if settings.LOCAL_MODE :
            return Redis(
                host = settings.PUBSUB_HOST,
                port = settings.PUBSUB_PORT,
                password = settings.PUBSUB_PASSWORD,
                db = 0
            )
        
        else :
            sentinelConnection = sentinel.Sentinel(
                [( settings.PUBSUB_HOST, settings.PUBSUB_PORT )],
                sentinel_kwargs = {"password" : settings.PUBSUB_PASSWORD}
            )

            try:
                master = sentinelConnection.discover_master("mymaster")
                print(master)
                if len(master) == 0 :
                    logging.error("No masters found")
                    return None 
                masterHost, masterPort = master

                #return the master connection
                return Redis(
                    host = masterHost,
                    port = masterPort,
                    password = settings.PUBSUB_PASSWORD,
                    db = 0
                )

            except Exception as e:
                logging.error(e)
                return None

    @staticmethod
    def UpdateAddition(sourceId, nodeData) :

        try:

            connection = PubSubUpdater.GetConnection()

            payload = {"command" : "add", "payload" : nodeData}

            key = "{}__{}".format(sourceId, ROUTING_PUBSUB)

            nReceivers = connection.publish(key, json.dumps(payload))

            log_publish(sourceId, "add", nReceivers)

            return True, "Published routing table"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def UpdateRemove(sourceId, nodeData) :

        try:

            connection = PubSubUpdater.GetConnection()

            payload = {"command" : "remove", "payload" : nodeData}

            key = "{}__{}".format(sourceId, ROUTING_PUBSUB)

            nReceivers = connection.publish(key, json.dumps(payload))

            log_publish(sourceId, "remove", nReceivers)

            return True, "Published routing table update"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def UpdateMultiSources(sourceIds, nodeData) :

        try:
            connection = PubSubUpdater.GetConnection()

            for sourceId in sourceIds :
                key = "{}__{}".format(sourceId, ROUTING_PUBSUB)
                payload = {"command" : "add", "payload" : nodeData}

                nReceivers = connection.publish(key, json.dumps(payload))
                log_publish(sourceId, "add", nReceivers)
            
            return True, "Publihed routing table"

        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def UpdateMetadata(sourceId, nodeTag, metadata) :

        try:
            connection = PubSubUpdater.GetConnection()

            key = "{}__{}".format(sourceId, ROUTING_PUBSUB)
            payload = {"command" : "meta_update", "payload" : {"nodeTag" : nodeTag, "metadata" : metadata}}

            nReceivers = connection.publish(key, json.dumps(payload))
            log_publish(sourceId, "meta_update", nReceivers)

            return True, "Published routing update"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GenericPublish(sourceId, command, payload) :

        try:

            connection = PubSubUpdater.GetConnection()

            key = "{}__{}".format(sourceId, ROUTING_PUBSUB)
            payload = {"command" : command, "payload" : payload}

            nReceivers = connection.publish(key, json.dumps(payload))
            log_publish(sourceId, command, nReceivers)

            return True, "Published, received by : {}".format(nReceivers)
            
        except Exception as e:
            logging.error(e)
            return False, str(e) 
    
    @staticmethod
    def GenericMultiPublish(sources, command, payload) :

        try:

            connection = PubSubUpdater.GetConnection()

            for source in sources :
                key = "{}__{}".format(source, ROUTING_PUBSUB)
                payload = {"command" : command, "payload" : payload}

                nReceiverss = connection.publish(key, json.dumps(payload))
                log_publish(source, command, nReceivers)

            return True, "Published to {} sources".format(sources)
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
