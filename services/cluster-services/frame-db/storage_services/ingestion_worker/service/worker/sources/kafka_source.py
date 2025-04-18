import os
import json
import kafka

from .base import BaseSourceType
from ..env import exit_on_failure, exit_on_success
import time

import logging
logging = logging.getLogger("MainLogger")

def kafka_source_validator(values):

    keys_required = [('host', str), ('port', int), ('queue_prefix', str), ('queue_names', list), ('includes_meta', bool), ('size_padding', int)]

    for key in keys_required:
        if key[0] not in values:
            logging.error("validation failed, missing field {}".format(key[0]))
            return False, "validation failed, missing field {}".format(key[0])
        
        if type(values[key[0]]) != key[1]:
            errMsg = "validation failed, key must be of type {} but got {}".format(
                key[1], type(values[key[0]])
            )
            logging.error(errMsg)
            return False, errMsg
    
    return True, "Validation passed"

class KafkaSource(BaseSourceType):

    def __init__(self, env, settings = {}, writer = None):
        super().__init__(env, settings, writer)

        self.set_pause_callback(self.pause_callback_fn)
        self.set_stop_callback(self.stop_callback_fn)

        self.queues = self.__get_part()

        #skip frame is not applicable to Redis source/Kafka source
        self.skip_frame = 0


    def stop_callback_fn(self, event):
        logging.info("Stop event detected")
        self.has_stop_request = True

        self.exit_on_success(self.status)

    def pause_callback_fn(self, event):
        logging.info("Pause event type detected")
        if event == "pause":
            self.is_paused = True
        else:
            self.is_paused = False
    
    def __get_part(self):

        def split(a, n):
            k, m = divmod(len(a), n)
            return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

        try:

            queues = self.settings['queue_names']
            
            n_workers = int(self.env.n_workers)
            current_index = int(self.env.worker_index)
            #apply the part rule:
            queue_parts = list(split(queues, n_workers))

            if current_index > (len(queue_parts) - 1):
                msg = "Current worker has no work, as it has no queue to listen to"
                logging.info(msg)
                self.exit_on_success({"errData" : msg})
            
            #get the current part :
            current_part = queue_parts[current_index]

            if len(current_part) == 0 :
                msg = "Current worker is not assigned to any queue, so it is not required"
                logging.info(msg)
                self.exit_on_success({"errData" : msg})

            prefix = self.settings['queue_prefix']

            #attach the prefix:
            current_part_prefixed = ["{}{}".format(prefix, part) for part in current_part]
            return current_part_prefixed

        except Exception as e:
            logging.error(e)
            errMsg = "failed to get the part"
            self.exit_on_failure({"errMsg" : errMsg})


    def update_status(self, **kwargs):
        self.status['frames_produced'] = self.frame_count
        self.status['frames_written'] = self.considered_frames

        if 'frames_per_part' not in self.status:
            self.status['frames_per_part'] = {}
        
        #add keys
        part = kwargs['part']

        self.status['frames_per_part'][part] = self.status['frames_per_part'].get(part, 0) + 1
    

    def __generate_key(self, part_name, seq_number = None, failure = False, source_id = None):

        part_key = "{}__kaf__{}__{}".format(
            self.env.key_prefix,
            self.source_id if not source_id else source_id,
            part_name
        )

        key_seq = seq_number
        
        return "{}__{}".format(part_key, key_seq)

    def __pause_lock(self):
        while self.is_paused:
            logging.info("Source is in paused state")
            time.sleep(5)

    def parse_data(self, data):
        if not self.settings['includes_meta']:
            return data, None
        
        #start parsing metadata
        padding_length = self.settings['size_padding']
        llen = data[:padding_length]
        llen = int.from_bytes(llen, byteorder = "big")

        frame_data = data[padding_length : padding_length + llen]

        remaining_end_marker = padding_length + llen
        metadata = data[remaining_end_marker:]
        metadata = metadata.decode('utf-8')

        #print(frame_data)

        print(metadata, len(metadata))

        return frame_data, json.loads(metadata)
        
    def validation_function(self, metadata, frame_data):
        
        for key in metadata :
            if key in frame_data:
                if metadata[key] != frame_data[key]:
                    return False

        return True
    
    def runner(self):

        while True:
            
            try:

                kafkaConsumer = kafka.KafkaConsumer(
                    *self.queues,
                    bootstrap_servers = "{}:{}".format(self.settings['host'], self.settings['port']),
                    client_id = os.getenv("HOSTNAME", self.env.job_name)
                )

                print('connected to kafka')

                for consumer_record in kafkaConsumer:

                    if self.has_stop_request:
                        return True, self.status

                    self.__pause_lock()

                    topic = consumer_record.topic
                    key = consumer_record.key

                    if self.should_skip_frame():
                        continue

                    frame_data = consumer_record.value
                    
                    frame_data, metadata = self.parse_data(frame_data)

                    source_id = metadata['source_id'] if 'source_id' in metadata else self.source_id

                    print('Got new source {}'.format(source_id))

                    seq_number = self.get_frame_count(source_id)

                    seq_number = seq_number + self.get_start_seq(source_id)

                    #update sequence number
                    self.update_frame_count(source_id)

                    frame_metadata = {
                        "seq_no" : self.frame_count,
                        "part" : topic,
                        "size" : len(frame_data),
                        "ext" : metadata['ext'] if 'ext' in metadata else 'raw',
                        "task" : "kafka",
                        "source_id" : source_id,
                        "frame_seq_number" : seq_number
                    }

                    print(source_id, seq_number)

                    should_validate = self.env.enable_validation and self.settings['include_meta']

                    if should_validate and (not self.is_valid_frame(metadata)):
                        if self.env.enable_corrupt_persistence:
                            frame_key = self.__generate_key(topic, seq_number = seq_number, failure = True, source_id = source_id)
                            self.write_failure_frame(
                                frame_key,
                                frame_data,
                                frame_metadata,
                                metadata
                            )
                        continue

                    self.mark_frame_as_proper()

                    frame_key = self.__generate_key(topic, seq_number = seq_number, failure = False, source_id = source_id)
                    self.write_success_frame(
                        frame_key,
                        frame_data,
                        frame_metadata,
                        metadata
                    )

                    self.update_status(part = topic)

                    if self.env.frame_limit != -1 and self.frame_count >= self.env.frame_limit:
                        if self.env.enable_batch_pause:

                                logging.info("Paused after writing {} frames".format(self.env.frame_limit))
                                self.is_paused = True

                                self.frame_count = 0
                        else:
                            return True, self.status
                
            except Exception as e:
                logging.error(e)
                time.sleep(10)
                continue
    
    def run(self):

        try:
            ret, result = self.runner()
            return ret, result
        except Exception as e:
            logging.error(e)
            self.exit_on_failure({"errData" : "task encountered an unknonwn issue {}".format(e)})
            
