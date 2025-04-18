import json
from ..pythreads import pythread
import logging
from queue import Queue
import redis
import time
import copy

logging = logging.getLogger("MainLogger")


class ActuationController:

    def __init__(self, sourceID, actuation_queue_params):
        self.actuation_queue_params = actuation_queue_params
        self.redis_connection = redis.Redis(
            host=actuation_queue_params['host'],
            port=actuation_queue_params['port'],
            db=0,
            password=actuation_queue_params['password']
        )

        self.current_seq_number = 0
        self.batch_size = 0
        self.source_id = sourceID

        self.current_seqs = []
        self.current_keys = []
        self.ts = []

        self.activated = False

        self.message_queue = Queue(100)
        self.queue_name = "{}__act_queue".format(self.source_id)

        # start the actuation queue thread
        self.__internal_push_to_queue(self)
        logging.info("Initialized actuation queue pusher")

    def reset_config(self, config_data):
        self.current_seq_number = 0
        if not config_data:
            self.activated = False
            return
        else:
            self.activated = True
        self.batch_size = config_data['act_batch_size']

    @pythread
    def __internal_push_to_queue(self):
        while True:
            try:
                data = self.message_queue.get()

                # push to the connection:
                data_encoded = json.dumps(data).encode('utf-8')
                if self.redis_connection:
                    self.redis_connection.lpush(
                        self.queue_name,
                        data_encoded
                    )

                logging.info("Pushed actuation message {}".format(
                    data['actuationSeq']
                ))
            except Exception as e:
                logging.error("Failed to push actuation message, reconnecting")
                logging.error(e)
                self.redis_connection = redis.Redis(
                    host=self.actuation_queue_params['host'],
                    port=self.actuation_queue_params['port'],
                    password=self.actuation_queue_params['password'],
                    db=0
                )

    def update(self, seq_number, key_prefix):


        if not self.activated:
            return

        self.current_seqs.append(seq_number)
        self.current_keys.append(key_prefix)
        self.ts.append(time.time())

        if len(self.current_seqs) % self.batch_size == 0:
            # prepare packet:
            packet = {
                "sourceID": self.source_id,
                "actuationSeq": self.current_seq_number,
                "keys": copy.copy(self.current_keys),
                "seq": copy.copy(self.current_seqs),
                "ts": copy.copy(self.ts)
            }

            self.message_queue.put(packet)
            self.current_seq_number += 1
            self.current_seqs.clear()
            self.current_keys.clear()
            self.ts.clear()
