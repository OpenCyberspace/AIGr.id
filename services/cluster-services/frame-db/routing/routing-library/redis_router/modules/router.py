import os
import json
import redis
from redis.sentinel import Sentinel
import requests
import time
from queue import Queue
import plyvel
from .actuator import ActuationController

import logging
logging.basicConfig(level = logging.INFO)


TEST_MODE_RUN = True if os.getenv("TEST_MODE", "No").lower() == "yes" else False

ENABLE_LOCAL_BUFFERING = True if os.getenv("ENABLE_BUFFERING", "No").lower() == "yes" else False

if ENABLE_LOCAL_BUFFERING :
    logging.info("Running with local-buffer ON, this will store all frames in local buffer if failure is detected, buffering will work only if async=true")


ENABLE_HEALTH_CHECK = True if os.getenv("ENABLE_HEALTH_CHECK", "No").lower() == "yes" else False

if ENABLE_HEALTH_CHECK :
    logging.info("Health check enabled, all threads will be respawned if they fail")

if TEST_MODE_RUN :
    logging.info("Running in test mode, will generate keys with framedb index")

PERSISTENT_FAILURES = True if os.getenv("PERSISTENT", "No").lower() == "yes" else False
if PERSISTENT_FAILURES :
    logging.info("Enabled framedb-persistence, all failed writes will be persisted")


ENABLE_UPDATE_REQUESTS = True if os.getenv("ENABLE_UPDATE_REQUESTS", "No").lower() == "yes" else False
MINIMUM_BACKLOG_FRAMES = int(os.getenv("MINIUM_FAILED_WRITES", 10))


from ..pythreads import pythread
from .sockets import RedisSockets, AsyncRedisSockets
from .persistence import DISK_LOADER_IMPL, DISK_WRITER_IMPL
from .failure_persist import EncodedDataWriter
from .back_preassure import BackPreassureHandler


class UpdateRequester :

    def __init__(self, update_host, update_uri, sourceId, n_backlog_frames = 10, custom_notification_function = None ) :

        self.n_backlog_frames = n_backlog_frames
        self.custom_notification_function = custom_notification_function

        self.backlog_count = {}

        self.update_host = update_host
        self.update_uri = update_uri

        self.sourceId = sourceId

        if PERSISTENT_FAILURES :
            self.db_handle = EncodedDataWriter.create_db_handle(source = self.sourceId)


    

    def __request_updates(self, update_host, update_uri, sourceId, framedbId) :

        URI = "{}/{}".format(update_host, update_uri)
 
        try:
            payload = {'sourceId' : sourceId, 'nodeTag' : framedbId}
            response = requests.post(url = URI, json = payload)

            response = response.json()

            if not response['success'] :
                logging.error("Failed to update")
                return False, "Failed to update"
            
            return True, "Update requested"

        except Exception as e:
            logging.error(e)
            return False, str(e)
        


    def on_notification(self, key, timestamp, event_name, framedb_id, exception_obj = None, command = None, data = None) :
        
        if  event_name == "framedb_write_failed" and  exception_obj and ENABLE_UPDATE_REQUESTS :
            logging.info("Called err handler for {}".format(key))
            #handle exception by increasing the backlog count
            self.backlog_count[framedb_id] = self.backlog_count.get(framedb_id, 0) + 1
            if self.backlog_count >= self.n_backlog_frames :
                self.backlog_count[framedb_id] = 0
                ret, resp = self.__request_updates(self.update_host, self.update_uri, self.sourceId, framedb_id)
                if not ret :
                    logging.error(resp)
            
            #failed write, so persist in the DB
            if PERSISTENT_FAILURES :
                ret = EncodedDataWriter.write_frame_to_disk(self.sourceId, framedb_id, key, data, command, self.db_handle)
                if not ret :
                    logging.error("failed to persist frame to db")
                    os._exit(0)
            
            if self.custom_notification_function :
                self.custom_notification_function(key, timestamp, event_name, framedb_id, exception_obj)
                        
        elif event_name == "framedb_write_success" :
                
            logging.info("Frame with key {} wrote successfully at : {} to {}".format(
                key, timestamp, framedb_id
            ))

            if self.custom_notification_function :
                self.custom_notification_function(key, timestamp, event_name, framedb_id, exception_obj)
                


def GetIntialRoutingTable(sourceId, routingServiceUri, apiRoute = "/routing/getMapping") :

    payload = {'sourceId' : sourceId}
    
    URI = "{}{}".format(routingServiceUri, apiRoute)

    try:

        response = requests.post(URI, json = payload)
        response = response.json()

        print(response)

        if not response['success'] :
            return False, "Request failed, maybe {} does not exist".format(sourceId)
        
        return True, response['result']['framedbNodes']
        
    except Exception as e:
        logging.error(e)
        return False, str(e)


def CreateRedisSocket(entry, entryData, on_notification_handle = None, async_mode = False, sourceId = None) :

    ret = False; socket = None

    if not async_mode :
        ret, socket = RedisSockets.create_redis_socket(
            host = entryData['masterIP'],
            port = entryData['redisPort'],
            password = os.getenv("REDIS_PASSWORD", "Friends123#"),
            db = 0
        )

        if not ret :
            logging.error("Failed creating socket for {}".format(entry))
            os._exit(0)
    else :
        socket = AsyncRedisSockets(
            host = entryData['masterIP'],
            port = entryData['redisPort'],
            password = os.getenv("REDIS_PASSWORD", "Friends123#"),
            db = 0,
            enable_buffering = ENABLE_LOCAL_BUFFERING,
            framedb_name = entry,
            custom_notification_callback = on_notification_handle,
            sourceId = sourceId
        )

        if not socket :
            logging.error("Failed to create socker for {}".format(entry))
            os._exit(0)

    logging.info("Created redis socket for {}".format(entry))
    
    return socket


def ReinitSocketWithLock(oldSocket, entry, entryData, async_mode = False) :

    if not async_mode :
        return CreateRedisSocket(entry, entryData, async_mode)
    
    oldSocket.updateConnection(
        host = entryData['masterIP'],
        port = entryData['redisPort'],
        password = os.getenv("REDIS_PASSWORD", "Friends123#"),
        db = 0
    )

    return oldSocket


def GetInitialTable(sourceId, routingService, on_notification_handle = None,  async_mode = False, table_only = False) :

        ret, response = GetIntialRoutingTable(sourceId, routingService['uri'], routingService['api'])

        if not ret :
            logging.error("Failed to get initial routing table, so it will be empty")
            return dict()
    
        #parse routing table
        routingTableDict = {data['nodeTag'] : data for data in response}

        #create redis socket for eacj entry of the routing table:

        if table_only :
            return routingTableDict

        for entry in routingTableDict :

            entryData = routingTableDict[entry]
            socket = CreateRedisSocket(entry, entryData, on_notification_handle, async_mode, sourceId = sourceId)
            routingTableDict[entry]['socket'] = socket 
            routingTableDict[entry]['bp'] = False

        return routingTableDict


def DiscoverMaster(instanceInfo : dict) :

    try:

        host = instanceInfo['host']
        port = instanceInfo['port']
        password = instanceInfo['password']

        sentinelConnection = Sentinel([(host, port)], sentinel_kwargs = {"password" : password})
        master = sentinelConnection.discover_master("mymaster")
        master_ip, master_port = master

        return master_ip, master_port
        
    except Exception as e:
        logging.error(e)
        return False, str(e)


class RedisRouter :

    def __init__(self, sourceId : str, routingService : dict = {}, enableUpdates = True, updateChannelData : dict = {}, custom_notifications = None, asynchronous = False) :

        self.sourceId = sourceId

        self.custom_notifications = custom_notifications

        if 'isSentinel' in updateChannelData and updateChannelData['isSentinel'] :
            self.__update_master_address(updateChannelData)
            print(updateChannelData)

        self.updaterModule = UpdateRequester(routingService['uri'], routingService['update_api'], self.sourceId, n_backlog_frames = MINIMUM_BACKLOG_FRAMES, custom_notification_function = self.custom_notifications)
        self.callback = self.updaterModule.on_notification

        self.routingTable = GetInitialTable(sourceId, routingService, self.callback, asynchronous)
        #self.routingTable = {}

        self.enableUpdates = enableUpdates
        self.asynchronous = asynchronous

        self.routingService = routingService

        self.updateChannelData = updateChannelData

        if not self.enableUpdates :
            self.routingTable = GetInitialTable(sourceId, routingService, self.callback, asynchronous)

        print(self.routingTable)

        if self.enableUpdates :

            self.updateChannel = os.getenv("UPDATE_CHANNEL", "routing_updates")
            self.thread_wrapper = self.init_updater(self)
            
        
        self.routerLock = False
        self.bp_enabled = False
        self.bp_handle = None

        self.temp_wait = False

        self.localBuffer = list()

        # enable actuation controller:
        self.act_controller = ActuationController(
            sourceId, routingService['act_params']
        )

        # set initial metadata:
        metadata = self.get_metadata()
        if metadata:
            self.act_controller.reset_config(
               metadata
            )


    def __update_master_address(self, instanceDetails : dict) :

        logging.info("Sentinel info provided, discovering master for pub-sub")


        host, port = DiscoverMaster(instanceDetails)

        if not host :
            logging.error("No masters found for {}:{}".format(instanceDetails['host'], instanceDetails['port']))
            os._exit(0)

        instanceDetails['host'] = host 
        instanceDetails['port'] = port 
    
    
    def __updateTable(self, routingData) :

        command = routingData['command']
        payload = routingData['payload']

        print(command, payload)

        if command == "remove" :
            
            #update table with lock
            self.routerLock = True

            for framedb in payload :
                self.routingTable.pop(framedb, None)
            
            #release the lock once done
            self.routerLock = False
        
        elif command == "add" or command == "update" :

            self.routerLock = True

            for framedb in payload :
                framedbId = framedb['nodeTag']

                #if framedbId already exists, get its socket object and assign it to updated routing table:
                if framedbId in self.routingTable :

                    #get the object reference and update the table :
                    connection_object = self.routingTable[framedbId]['socket']
                    connection_object = ReinitSocketWithLock(connection_object, framedbId, framedb, self.asynchronous)
                    self.routingTable[framedbId] = framedb
                    self.routingTable[framedbId]['socket'] = connection_object
                    self.routingTable[framedbId]['bp'] = False

                    logging.info("Updated routing table with old object")

                else :
                #create a socket for the connection:
                    socket = CreateRedisSocket(framedbId, framedb, self.callback , self.asynchronous, sourceId = self.sourceId)
                    self.routingTable[framedbId] = framedb
                    self.routingTable[framedbId]['socket'] = socket
                    self.routingTable[framedbId]['bp'] = False
            self.routerLock = False
        

        elif command == "bp_on" :

            self.routerLock = False

            nodeTag = payload['nodeTag']

            if nodeTag in self.routingTable :

                if 'cluster_name' in payload :
                    if self.routingTable[nodeTag]['cluster_name'] != payload['cluster_name'] :
                        if not self.routingTable[nodeTag]['bp'] :
                            self.routingTable[nodeTag]['socket'].enable_back_preassure()
                            self.routingTable[nodeTag]['bp'] = True

                elif not self.routingTable[nodeTag]['bp'] :
                    self.routingTable[nodeTag]['socket'].enable_back_preassure()

                    self.routingTable[nodeTag]['bp'] = True

            self.routerLock = False

        elif command == "bp_off" :

            self.routerLock = False

            nodeTag = payload['nodeTag']

            if nodeTag in self.routingTable :

                if 'cluster_name' in payload :
                    if self.routingTable[nodeTag]['cluster_name'] != payload['cluster_name'] :
                        if self.routingTable[nodeTag]['bp'] :
                            self.routingTable[nodeTag]['socket'].disable_back_preassure()

                            self.routingTable[nodeTag]['bp'] = False


                elif self.routingTable[nodeTag]['bp'] :
                    self.routingTable[nodeTag]['socket'].disable_back_preassure()

                    self.routingTable[nodeTag]['bp'] = False

            self.routerLock = False

        elif command == "bp_source_off" :
            if self.bp_enabled :
                self.__read_from_bp_db(self)
            logging.info("Turned off back preassure for source={}".format(self.sourceId))

        elif command == "bp_source_on" :
            if not self.bp_enabled :
                self.__bp_enable_source()
            logging.info("Turned on back preassure for source={}".format(self.sourceId))

        elif command == "meta_update" :

            self.routerLock = True

            nodeTag = payload['nodeTag']
            if nodeTag in self.routingTable :
                self.routingTable[nodeTag]['metadata'] = payload['metadata']

            self.routerLock = False
        else :
            print('Unknown commnad {} received'.format(command))

        logging.info(str(self.routingTable))
        # update the actuation controller:
        self.act_controller.reset_config(self.get_metadata())
    @pythread
    def init_updater(self) :

        #update routing table
        #self.routingTable = GetInitialTable(self.sourceId, self.routingService, self.custom_notifications, self.asynchronous)
        
        #create redis pub-sub on update channel{
        sourceChannel = "{}__{}".format(self.sourceId, self.updateChannel)

        #create a redis connection and subscribe to events
        pubsubConnection = redis.Redis(
            host = self.updateChannelData['host'],
            port = self.updateChannelData['port'],
            password = self.updateChannelData['password'],
            db = self.updateChannelData['db']
        )

        pubsubConnection = pubsubConnection.pubsub()

        #subscribe to channel :
        pubsubConnection.subscribe(sourceChannel)

        print('Started routing table update channel')

        for item in pubsubConnection.listen() :

            #print(item)

            #handle ack message upon connection
            if item['type'] == 'subscribe' and item['data'] == 1 :
                print('Pubsub connection successful')
    
            #validate the message
            if item['type'] == "message" and item['channel'].decode('utf-8') == sourceChannel :

                data = item['data']
                if type(data) == bytes:
                    data = json.loads(data.decode('utf-8'))
                # call table update
                self.__updateTable(data)

    def __write_to_socket_2(self, key: str, data, op: str, nodeTag: str):
        while self.routerLock:
            logging.info("router lock detected, waiting for table update")
            time.sleep(1/1000)
        socket = self.routingTable[nodeTag]['socket']
        if op == "set":
            socket.set(key, data)
        elif op == "lpush":
            socket.lpush(key, data)
        elif op == "rpush":
            socket.rpush(key, data)
        else:
            logging.error("Invalid op {} detected. Exiting. Supported ops are : set, lpush and rpush".format(op))
            os._exit(0)

    def __write_to_socket(self, key : str, data , op : str,  generate_test_key = False) :

        while self.routerLock :
            logging.info("router lock detected, waiting for table update")
            time.sleep(1/1000)

        for entry in self.routingTable :
            socket = self.routingTable[entry]['socket']

            if TEST_MODE_RUN :
                key_gen = "{}_{}_{}".format()
                
                if op == "set" :
                    socket.set(key_gen, data)
                
                elif op == "lpush" : 
                    socket.lpush(key_gen, data)
                
                elif op == "rpush" :
                    socket.rpush(key_gen, data)
                else :
                    logging.error("Invalid op {} detected. Exiting. Supported ops are : set, lpush and rpush".format(op))
                    os._exit(0)

                logging.info("Pushed test mode key {}".format(key_gen))
                continue
            
            if op == "set" :
                socket.set(key, data)
            elif op == "lpush" :
                socket.lpush(key, data)
            elif op == "rpush" :
                socket.rpush(key, data)
            else :
                logging.error("Invalid op {} detected. Exiting. Supported ops are : set, lpush and rpush".format(op))
                os._exit(0)
    

    def __health_check_pub_sub(self) :

        if self.thread_wrapper and not self.thread_wrapper.is_alive() :
            self.thread_wrapper = self.init_updater(self)
            logging.info("pub-sub updated has failed, and it is respawned")
    

    def __bp_enable_source(self) :

        self.bp_enabled = True

        #create back-preassure handler :
        self.bp_handle = BackPreassureHandler.create_handle(self.sourceId)
        logging.info("Back preassure enabled for source={}".format(
            self.sourceId
        ))
    
    @pythread
    def __read_from_bp_db(self) :

        logging.info("Restoring from Back preassure db")

        self.bp_enabled = False

        if self.bp_handle :
            DISK_WRITER_IMPL.close_handler(self.bp_handle)

        self.bp_handle = None

        self.temp_wait = True

        count = 0

        #restore data from bp queue
        for key_prefix, command, data in BackPreassureHandler.read_by_prefix(self.sourceId, "source_all") :

            self.__write_to_socket(key_prefix, data, command, generate_test_key = TEST_MODE_RUN)
            count +=1
        

        #This is important!!
        self.temp_wait = False


        logging.info("Restored {} frames".format(count))


    
    def put(self, sourceId, key, data, op = "set") :
    
        if len(self.routingTable) == 0 or self.temp_wait :
            self.localBuffer.append((key, data))
            logging.warning("No destinations found in the routing table, saving in local buffer queue - length {}".format(
                len(self.localBuffer)
            ))
        
        else :

            #if length of localbuffer is not zero, then pop its contents until it becomes zero and write to the socket
            while len(self.localBuffer) != 0 :
                poppedKey, poppedData = self.localBuffer.pop(0)
                self.__write_to_socket(poppedKey, poppedData, op = op, generate_test_key = TEST_MODE_RUN)
            
            #since localBuffer is not emptied, push original data

            if self.bp_enabled :
                BackPreassureHandler.write_frame_to_db(self.bp_handle, key, "source_all", data, op)
            else :
                self.__write_to_socket(key, data, op = op, generate_test_key = TEST_MODE_RUN)

            if ENABLE_HEALTH_CHECK :
                self.__health_check_pub_sub()

    
    def __write_mapped(self, mapped_data_dict : dict, op : str = "set", test_mode : bool = False) :
        
        for nodeTag in mapped_data_dict :
            write_data = mapped_data_dict[nodeTag]
            for key, value in write_data['data'].items():
                self.__write_to_socket_2(key, value, op, nodeTag)
        

    def mapped_put(self, sourceId : str, data_dict : dict, op : str = "set") :

        if len(self.routingTable) == 0 :
            self.localBuffer.append(data_dict)
            logging.warning("No destinations found in the routing table, saving in local buffer queue - length {}".format(
                len(self.localBuffer)
            ))
        
        else :

            while len(self.localBuffer) != 0 :
                poppedDataDict = self.localBuffer.pop(0)
                self.__write_mapped(poppedDataDict, op = op, test_mode = TEST_MODE_RUN)
            
            #since local buffer is emptied, push the original data
            self.__write_mapped(data_dict, op = op, test_mode = TEST_MODE_RUN)

    def get_routing_table(self) :
        
        while self.routerLock :
            time.sleep(1/1000)
        
        formatted_output = {}
        for nodeTag in self.routingTable :

            nodeData = self.routingTable[nodeTag]
            formatted_output[nodeTag] = {
                "cluster_name" : nodeData['cluster_name'], 
                "metadata" : nodeData['metadata']
            }
        
        return formatted_output
    
    def get_metadata(self) :

        while self.routerLock :
            time.sleep(1/1000)
        
        formatted_metadata_op = {}

        if len(self.routingTable) == 0 :
            return None
        
        for key in self.routingTable :
            if self.routingTable[key]['metadata'] and self.routingTable[key]['metadata'] != {} :
                return self.routingTable[key]['metadata']
        else :
            return None
        
    


class RedisRouterReader :

    def __init__(self, sourceId : str, nodeTag : str, routingService : dict, notification_callback = None) :

        self.sourceId = sourceId
        self.nodeTag = nodeTag
        self.routingService = routingService

        self.notification_callback = notification_callback

        self.initialTable = GetInitialTable(
            self.sourceId, routingService,
            on_notification_handle = self.notification_callback,
            async_mode = False,
            table_only = True
        )

        self.nodeTag = nodeTag

        self.READ_FAIL_EVENT  = "FRAMEDB_READ_FAIL"
        self.READ_SUCCESS_EVENT = "FRAMEDB_READ_SUCCESS"
    

    def __impl_get(self, connection : redis.Redis, key : str, key_gen_function = None) :

        try:

            while True :
               data = connection.get(key)

               if not data :
                   time.sleep(2/1000)
                   continue
               
               if self.notification_callback :
                   self.notification_callback(key, time.time(), self.READ_SUCCESS_EVENT, None)
            
               yield key, data

               if key_gen_function :
                   key = key_gen_function(key)
            
        except Exception as e:
            logging.error(e)
            if self.notification_callback :
                self.notification_callback(key, time.time(), self.READ_FAIL_EVENT, e)
        
    
    def __impl_lpop(self, connection : redis.Redis, key : str) :

        try:
            while True :

                data = connection.lpop(key)
                if self.notification_callback :
                    self.notification_callback(key, time.time(), self.READ_SUCCESS_EVENT, None)
                
                yield key, data 
        
        except Exception as e :
            logging.error(e)
            if self.notification_callback :
                self.notification_callback(key, time.time(), self.READ_FAIL_EVENT, e)


    
    def __impl_rpop(self, connection : redis.Redis, key : str) :

        try:

            while True :

                data = connection.rpop(key)
                if self.notification_callback :
                    self.notification_callback(key, time.time(), self.READ_SUCCESS_EVENT, None)
                
                yield key, data
            
        except Exception as e:
            logging.error(e)
            if self.notification_callback :
                self.notification_callback(key, time.time(), self.READ_FAIL_EVENT, e)
    


    
    def get(self, key, operation = "get", key_gen_function = None) :

        #filter by nodeTag :

        connectionData = [self.initialTable[framedbId] for framedbId in self.initialTable if framedbId == self.nodeTag]
        if len(connectionData) == 0 :
            return False, "Node {} is not receiving any frames from source {}".format(self.nodeTag, self.sourceId)
        
        connectionData = connectionData[0]
        connection = RedisSockets.create_redis_socket(
            host = connectionData['masterIP'],
            port = connectionData['redisPort'],
            password = os.getenv("REDIS_PASSWORD", "Friends123#"),
            db = 0
        )

        if operation == "get" :

            while True :

                yield self.__impl_get(connection, key, key_gen_function)
            
        elif operation == "lpop" :

            while True :

                yield self.__impl_lpop(connection, key)
        
        elif operation == "rpop" :

            while True :

                yield self.__impl_rpop(connection, key)
        else :

            logging.error("Invalid ops, supported ops are = [get, lpop, rpop]")
    
