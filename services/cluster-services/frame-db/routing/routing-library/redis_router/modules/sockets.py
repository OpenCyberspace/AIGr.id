import redis
import logging
from queue import Queue
import os 
import time
from .persistence import DISK_WRITER_IMPL, DISK_LOADER_IMPL
from .failure_persist import EncodedDataReader
from .back_preassure import BackPreassureHandler
from ..pythreads import pythread

logging = logging.getLogger("MainLogger")


EVENT_TYPE_FAILURE = "framedb_write_failed"
EVENT_TYPE_SUCCESS = "framedb_write_success"

PERSISTENT_FAILURES = True if os.getenv("PERSISTENT", "No").lower() == "yes" else False

request_update_on_error = True if os.getenv("REQUEST_UPDATES", "Yes").lower() == "yes" else False

ENABLE_HEALTH_CHECK = True if os.getenv("ENABLE_HEALTH_CHECK", "No").lower() == "yes" else False


class RedisSockets :

    @staticmethod
    def create_redis_socket(host, port, password, db = 0) :

        try:

            redisConnection = redis.Redis(
                host, port, password = password, db = 0, socket_keepalive = True,
                socket_connect_timeout = 100
            )

            return True, redisConnection
            
        except Exception as e:
            logging.error(e)
            return False, str(e)



class Pinger :

    @staticmethod
    def PingConnection(connection = None, host = None, port = None, password = None) :

        try:

            if connection :
                #connection object is provided, call ping on the connection directly without creating a new one
                return connection.ping()
            else :
                #create a new connection and then call ping
                connection = redis.Redis(host, port, password = password, db = 0)
                return connection.ping()
            
        except Exception as e:
            logging.error(e)
            return False 
    


class AsyncRedisSockets :

    def __init__(self, host, port, password, db = 0, enable_buffering = False, framedb_name = None, custom_notification_callback = None, sourceId = None) :

        ret, connection = RedisSockets.create_redis_socket(host, port, password, db = 0)
        if not ret :
            logging.error("Failed to create redis socket for {}:{}".format(host, port))
            os._exit(0)
        
        self.connection = connection

        self.__queue = Queue(100)
        self.__op_table = {
            "set" : self.connection.set,
            "lpush" : self.connection.lpush,
            "rpush" : self.connection.rpush
        }

        self.enable_buffering = enable_buffering

        self.local_buffer_queue = []

        self.host = host 
        self.port = port

        self.updateLock = False
        self.sourceId = sourceId

        self.bp_enabled = False

        #start work-executor
        self.work_loop_wrapper = self.__work_loop(self)
        logging.info("Created asynchronous socket for {}:{}".format(host, port))

        self.framedb_name = framedb_name

        if PERSISTENT_FAILURES :
            self.populate_queue(sourceId, framedb_name)

        self.custom_notification_callback = custom_notification_callback

        self.bp_handle = None
    

    def populate_queue(self, sourceId : str, framedb_name : str) :
        
        #read by prefix
        logging.info("Searching for persistent/left-over keys in the database")

        global DISK_LOADER_IMPL

        if not DISK_LOADER_IMPL :
            logging.error("Persistence is turned-on, but no disk loader class is provided, exiting")
            os._exit(0) 

        count = 0

        #iterate with prefix and get all the keys 
        for key_suffix, command, data in EncodedDataReader.read_by_prefix(self.sourceId, framedb_name) :

            #push to the queue
            self.__queue.put((command, key_suffix, data))
            count +=1
        logging.info("Restored {} failed-write frames from persistent db".format(count))
    

    def populate_from_bp_queue(self, sourceId : str, framedb_name : str) :

        logging.info("Loading from back-preassure db")

        global DISK_LOADER_IMPL

        if not DISK_LOADER_IMPL :
            logging.error("Persistence is turned-off, but no disk loader class is provided, exiting")
            os._exit(0)
        count = 0

        for key_suffix, command, data in BackPreassureHandler.read_by_prefix(sourceId, framedb_name) :

            #push to queue
            self.__queue.put((command, key_suffix, data))
            count +=1
        
        logging.info("Restored {} failed-write frames from persistent db".format(
            count
        ))

    
    def set(self, key, data) :
        self.__queue.put(("set", key, data))

        if ENABLE_HEALTH_CHECK and self.work_loop_wrapper and self.work_loop_wrapper.is_alive() :
            self.work_loop_wrapper = self.__work_loop()
            logging.info("work-loop was not alive, respawned")
    
    def lpush(self, key, data) :
        self.__queue.put(("lpush", key, data))

        if ENABLE_HEALTH_CHECK and self.work_loop_wrapper and not self.work_loop_wrapper.is_alive() :
            self.work_loop_wrapper = self.__work_loop()
            logging.info("work-loop was not alive, respawned")
    
    def rpush(self, key, data) :
        self.__queue(("rpush", key, data))

        if ENABLE_HEALTH_CHECK and self.work_loop_wrapper and not self.work_loop_wrapper.is_alive() :
            self.work_loop_wrapper = self.__work_loop()
            logging.info("work-loop was not alive, respawned")

    def updateConnection(self, host, port, password, db = 0) :

        self.updateLock = True

        #update connection details:
        ret, connection = RedisSockets.create_redis_socket(host, port, password, db = 0)
        if not ret :
            logging.error("Failed to get Redis connection, exiting")
            os._exit(0)
        
        self.connection = connection

        #reinit the op table :
        self.__op_table = {
            "set" : self.connection.set,
            "lpush" : self.connection.lpush,
            "rpush" : self.connection.rpush
        }

        self.host = host
        self.port = port 

        #release the lock :
        self.updateLock = False
    

    def enable_back_preassure(self) :

        self.bp_enabled = True

        if not self.bp_handle :
            self.bp_handle = BackPreassureHandler.create_handle(self.sourceId)
    

    def disable_back_preassure(self) :

        self.bp_enabled = False
        
        DISK_WRITER_IMPL.close_handler(self.bp_handle)

        print('called back-preassure disabler')

        self.populate_from_bp_queue(self.sourceId, self.framedb_name)

        self.bp_handle = None


    @pythread
    def __work_loop(self) :

        while True :

           command, key, data = self.__queue.get()

           while self.updateLock :
               logging.info("Lock detected, waiting for lock to open")
               time.sleep(1/1000)
               
           try:
               while len(self.local_buffer_queue) > 0 and self.enable_buffering :

                   command_first, key_first, data_first = self.local_buffer_queue[0]

                   if self.bp_handle :
                        BackPreassureHandler.write_frame_to_db(self.bp_handle, key_first, self.framedb_name, data_first, command_first)
                   else :
                       self.__op_table[command_first](key_first, data_first)

                   #pop off the data because the statement that was supposed to throw exception has completed properly
                   #and the data is not required, because it is already pushed to framedb
                   self.local_buffer_queue.pop(0)

                   logging.info('local_buffer_length={} wrote_key={} queue_length={}'.format(
                       len(self.local_buffer_queue), key_first, self.__queue.qsize()
                   ))

                   if self.custom_notification_callback :
                       self.custom_notification_callback(key_first, time.time(), True, self.framedb_name, None, command = command_first, data = data_first)

               #push the current data
               if self.bp_enabled :
                   BackPreassureHandler.write_frame_to_db(self.bp_handle, key, self.framedb_name, data, command)
               else :
                   self.__op_table[command](key, data)

               #print(self.custom_notification_callback)

               if self.custom_notification_callback :
                   self.custom_notification_callback(key, time.time(), EVENT_TYPE_SUCCESS , self.framedb_name, None, command = command, data = data)

           except Exception as e:
               logging.error(e)
               #append current data on to the queue
               self.local_buffer_queue.append((command, key, data))
               logging.error("Source {}:{} rechable, pushing to local buffer saving key={} in local-buffer".format(
                   self.host, self.port, key
               ))

               #check if the host is alive by pinging:
               isInstanceAlive = Pinger.PingConnection(connection = self.connection)

               if not isInstanceAlive :
                   logging.error("Instance not alive")
                   if self.custom_notification_callback :
                       self.custom_notification_callback(key, time.time(), EVENT_TYPE_FAILURE, self.framedb_name, e, command = command, data = data)