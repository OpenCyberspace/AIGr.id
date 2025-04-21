from numpy import source
import redis
from redis import sentinel
import requests
import time
import json
import os
from queue import Queue

from .pythreads import pythread
from .aios_logger import AIOSLogger, ErrorSeverity


class ConnectionsCache:

    def __init__(self, env, logger: AIOSLogger):
        self.env = env
        self.logger = logger

        self.connections = {}

    def __resolve_uds_path(self, uds_name):
        path = os.path.join(
            self.env.uds_vmount,
            "{}.sock".format(uds_name)
        )

        if not os.path.exists(path):
            return False, None

        return True, path

    def __gen_redis_connection(self, opt, uds=False, cluster=False):

        master_ip = opt['host']
        master_port = opt['port']

        print(master_ip, master_port, opt['password'])

        if cluster:
            sentinel_c = sentinel.Sentinel(
                [(master_ip, master_port)],
                password=opt['password'],
                sentinel_kwargs={"password": opt['password']},
                socket_timeout=10
            )

            try:
                master = sentinel_c.discover_master("mymaster")
                # print(master)
                if len(master) == 0:
                    raise Exception("Failed to discover masters")
                master_ip, master_port = master
            except Exception as e:
                self.logger.error(
                    action="master_discovery",
                    severity=ErrorSeverity.HIGH,
                    message="Failed to discover master for {}".format(
                        master_ip
                    ),
                    exception=e,
                    extras={
                        "mdag_id": self.env.mdag_id,
                        "block_id": self.env.block_id
                    }
                )

                return None, None, None

        if not uds:
            connection = redis.Redis(
                host=master_ip,
                port=master_port,
                password=opt['password'],
                db=opt['db']
            )

            connection_dec_ref = redis.Redis(
                host=master_ip,
                port=master_port,
                password=opt['password'],
                db=opt['db']
            )

            connection_del = redis.Redis(
                host=master_ip,
                port=master_port,
                password=opt['password'],
                db=5
            )

            return connection, connection_dec_ref, connection_del
        else:
            connection = redis.Redis(
                unix_socket_path=opt['uds_path'],
                password=opt['password'],
                db=opt['db']
            )

            connection_dec_ref = redis.Redis(
                unix_socket_path=opt['uds_path'],
                password=opt['password'],
                db=opt['db']
            )

            connection_del = redis.Redis(
                unix_socket_path=opt['uds_path'],
                password=opt['password'],
                db=5
            )

            return connection, connection_dec_ref, connection_del

    def get_connection(self, pointer_key, opt={}, uds_name="", is_clust=False, ref=False, delc=False):

        if pointer_key not in self.connections:

            connection = None
            uds_path = None
            if self.env.enable_uds_connections:
                ret, p = self.__resolve_uds_path(uds_name)
                if ret:
                    uds_path = p

            if uds_path:
                opt['uds_path'] = uds_path

            # create connection:
            connection, connection_ref, connection_del = self.__gen_redis_connection(
                opt, True if uds_path else False, True
            )

            self.connections[pointer_key] = {
                "socket": connection,
                "socket_ref": connection_ref,
                "socket_del": connection_del,
                "opts": opt
            }

        if ref:
            return self.connections[pointer_key]['socket_ref']

        if delc:
            return self.connections[pointer_key]['socket_del']

        return self.connections[pointer_key]['socket']

    def is_in_cache(self, pointer_key):
        return (pointer_key in self.connections)


class FrameDB:

    def __init__(self, svc_params, env, logger: AIOSLogger):

        self.svc_params = svc_params
        self.env = env
        self.logger = logger
        self.connections_cache = ConnectionsCache(
            self.env, self.logger
        )

        self.fetch_queues = {}
        self.fetch_threads = {}
        self.callbacks = {}
        self.op_serializer = None
        self.fetch_queues_ref = {}
        self.required_sizes = []

    def set_required_sizes(self, sizes):
        self.required_sizes = sizes

    @pythread
    def decr_ref(self, sourceID):
        queue = self.fetch_queues_ref[sourceID]
        sourceID = sourceID

        while True:

            try:

                connection_ref = self.connections_cache.get_connection(
                    sourceID, ref=True
                )

                connection_del = self.connections_cache.get_connection(
                    sourceID, delc=True
                )

                while True:
                    data = queue.get()['keys']
                    keys = list(data.keys())

                    # decref on batch of keys:
                    pipe = connection_ref.pipeline()
                    n_sizes_arr = []
                    for key in keys:
                        decr_by, n_sizes = data[key]
                        n_sizes_arr.append(n_sizes)
                        pipe.decr(key, decr_by)
                    ops = pipe.execute()

                    print(ops)
                    k_to_del = []
                    for idx, op in enumerate(ops):
                        if op <= 0:
                            n_sizes = n_sizes_arr[idx]
                            k_to_del.append(keys[idx])
                            for size in n_sizes:
                                k = keys[idx]
                                k = "{}__{}".format(k[5:], size)
                                k_to_del.append(k)

                    # execute the pipeline if deleting is enabled:
                    print('Keys to delete: ', k_to_del)
                    if len(k_to_del) > 0:
                        if not self.env.use_del_svc:
                            connection_ref.unlink(*k_to_del)
                        else:
                            connection_del.lpush("del_queue", *k_to_del)

            except Exception as e:
                self.logger.error(
                    action="framedb_get_mapping",
                    severity=ErrorSeverity.HIGH,
                    exception=e,
                    message=str(e),
                    extras={
                        "block_id": self.env.block_id,
                        "mdag_id": self.env.mdag_id
                    }
                )

    @pythread
    def source_work_loop(self, sourceID):
        sourceID = sourceID
        queue = self.fetch_queues[sourceID]
        cb = self.callbacks[sourceID]

        while True:
            try:

                connection = self.connections_cache.get_connection(
                    sourceID
                )

                while True:
                    data = queue.get()
                    keys = data['keys']
                    k = data['k']

                    data = connection.mget(keys)
                    cb(
                        is_not_error=True,
                        frame_data=data,
                        frame_keys=keys,
                        **k,
                    )

            except Exception as e:
                self.logger.error(
                    action="framedb_get_mapping",
                    severity=ErrorSeverity.HIGH,
                    exception=e,
                    message=str(e),
                    extras={
                        "block_id": self.env.block_id,
                        "mdag_id": self.env.mdag_id
                    }
                )

    def __get_framedb_mapping(self, sourceID):
        try:

            URL = "{}/routing/getMapping".format(self.env.routing_url)
            payload = {"sourceId": sourceID}

            response = requests.post(
                URL, json=payload
            )

            if response.status_code != 200:
                raise Exception("Server Error, code={}".format(
                    response.status_code
                ))

            # get source mapping info:
            response = response.json()
            print(response)
            if not response['success']:
                raise Exception("Failed to get source mapping {}".format(
                    sourceID
                ))
            # return the mapping:
            return True, response['result']['framedbNodes']

        except Exception as e:
            self.logger.error(
                action="framedb_get_mapping",
                severity=ErrorSeverity.HIGH,
                exception=e,
                message=str(e),
                extras={
                    "block_id": self.env.block_id,
                    "mdag_id": self.env.mdag_id
                }
            )

            return False, e

    def __handle_new_connection(self, sourceID, nT=None, ck=None):

        ret, mappings = False, {}
        if self.env.mode == "test":
            ret = True
            mappings = [{
                "nodeTag": self.env.test_node_tag,
                "masterIP": "localhost",
                "port": 6379,
                "password": self.env.test_password,
                "db": 0
            }]

        else:
            # get mapping information for that sourceID
            ret, mappings = self.__get_framedb_mapping(sourceID)
            if not ret:
                return False, mappings

        # get the framedb instance of the node the block is in:
        current_node_tag = nT if nT else self.env.framedb_node_tag
        if len(mappings) == 0:
            self.logger.error(
                action="framedb_get_mapping",
                severity=ErrorSeverity.HIGH,
                exception=None,
                message="No mappings found for {}".format(sourceID),
                extras={
                    "block_id": self.env.block_id,
                    "mdag_id": self.env.mdag_id
                }
            )
            return False, "No mappings found"

        # check nodes:

        selectedInstance = None

        for mapping_entry in mappings:
            if mapping_entry['nodeTag'] == current_node_tag:
                selectedInstance = mapping_entry
                break
        else:
            self.logger.warning(
                action="framedb_get_mapping",
                message="No Local instance found for source {}".format(
                    "{}, selecting the first one.".format(sourceID)
                )
            )

            selectedInstance = mappings[0]

        # use those parameters to create a connection:
        connection = self.connections_cache.get_connection(
            sourceID if not ck else ck,
            opt={
                "host": selectedInstance['serviceIp'],
                "port": selectedInstance['sentinelPort'],
                "password": self.env.framedb_password,
                "db": 0
            },
            uds_name=selectedInstance['nodeTag']
        )

        print(connection)
        if not connection:
            return False, "Connect failed"

        # make a ping
        for i in range(0, self.env.framedb_ping_retries):

            try:

                ret = connection.ping()
                if not ret:
                    time.sleep(10/1000)
                    raise Exception("Ping Failed")

                # ping is successful, break the loop and return
                # the connection
                return True, connection

            except Exception as e:
                self.logger.error(
                    action="framedb_redis_connect",
                    severity=ErrorSeverity.LOW,
                    exception=e,
                    message="Reconnecting to redis instance at {}".format(
                        selectedInstance['masterIP']
                    ),
                    extras={
                        "block_id": self.env.block_id,
                        "mdag_id": self.env.mdag_id
                    }
                )
        else:
            self.logger.error(
                action="framedb_redis_connect",
                severity=ErrorSeverity.HIGH,
                exception=Exception("Failed to connect to Redis"),
                message="Failed Connect to Redis at {}, tried {} times".format(
                    selectedInstance['masterIP'], self.env.framedb_ping_retries
                )
            )

            return False, "Failed to connect to Redis"

    def register_frame_delete_channel(self, sourceID: str):

        if not self.connections_cache.is_in_cache(sourceID):
            ret, connection = self.__handle_new_connection(
                sourceID
            )

            if not ret:
                return False, connection

            # register the delete channel for that sourceID asynchronously
            self.fetch_queues_ref[sourceID] = Queue(500)
            self.decr_ref(self, sourceID)

            print('Registered new frames delete channel for {}'.format(
                sourceID
            ))

    def get_frames_from(self, sourceID: str, keys_suffixed: list):

        connection = None
        if not self.connections_cache.is_in_cache(sourceID):
            ret, connection = self.__handle_new_connection(
                sourceID
            )
            if not ret:
                return False, connection

            # register the delete channel for that sourceID asynchronously:
            self.fetch_queues_ref[sourceID] = Queue(500)
            self.decr_ref(self, sourceID)

            print('Registered new frames delete channel for {}'.format(
                sourceID
            ))

        else:
            connection = self.connections_cache.get_connection(
                sourceID
            )

        # we got the connection, issue MGET
        try:

            data = connection.mget(keys_suffixed)
            return True, data

        except Exception as e:
            self.logger.error(
                action="mget_frames",
                severity=ErrorSeverity.HIGH,
                exception=e,
                extras={
                    "mdag_id": self.env.mdag_id,
                    "block_id": self.env.block_id
                },
                message="Failed to get frames from FrameDB"
            )

            return False, str(e)

    def get_frames_async(self, sourceID: str, keys_suffixed: list, k: dict, cb):
        if sourceID not in self.fetch_queues:
            # register the source on-demand:
            if self.env.on_demand_connections:
                # create connection on the fly:
                ret, outcome = self.register_frames_channel(sourceID, cb)
                if not ret:
                    return False, "Source {} could not be resolved".format(
                        sourceID
                    )
            else:
                return False, "Source {} not registered".format(sourceID)

        self.fetch_queues[sourceID].put({
            "keys": keys_suffixed,
            "k": k
        })
        return True, "Fetch request submitted for source {}".format(
            sourceID
        )

    def register_frames_channel(self, sourceID, cb):
        if sourceID in self.fetch_threads:
            return True, "Source already exist"

        connection = None
        if not self.connections_cache.is_in_cache(sourceID):
            ret, connection = self.__handle_new_connection(
                sourceID
            )
            if not ret:
                return False, connection
        else:
            connection = self.connections_cache.get_connection(
                sourceID
            )

        # save the connection:
        self.fetch_queues[sourceID] = Queue(500)
        self.fetch_queues_ref[sourceID] = Queue(500)
        self.callbacks[sourceID] = cb

        # start source threads:
        self.decr_ref(self, sourceID)
        self.source_work_loop(self, sourceID)

        self.fetch_threads[sourceID] = True

        # return:
        return True, "Registered Callback for source {}".format(
            sourceID
        )

    def set_output_serializer(self, cb):
        self.op_serializer = cb

    def push_sync(self, connection, outputs):

        try:

            if self.op_serializer:
                ret, outputs = self.op_serializer(outputs)
                if not ret:
                    raise Exception("Failed to serialie outputs")

            # push in pipeline mode:
            pipeline = connection.pipeline()
            for key in outputs:
                data = outputs[key]
                pipeline.set(key, data)

            pipeline.execute()
            print('Wrote keys to FrameDB')

            return True, "Wrote keys to FrameDB"

        except Exception as e:
            self.logger.error(
                action="framedb_output_push",
                severity=ErrorSeverity.HIGH,
                message="Failed to push outputs",
                extras={
                    "mdag_id": self.env.mdag_id,
                    "block_id": self.env.block_id,
                    "payload": outputs
                },
                exception=e
            )

    def decr_batch_keys(self, sourceID, keys):
        if sourceID not in self.fetch_queues_ref:
            # initialize the deref connection:
            self.register_frame_delete_channel(sourceID)

        # push to work queue:
        self.fetch_queues_ref[sourceID].put({
            "keys": keys
        })
