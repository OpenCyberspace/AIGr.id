import os
import json

from .base import BaseSourceType
from ..env import exit_on_failure, exit_on_success
import time

import logging
logging = logging.getLogger("MainLogger")


def fs_validator(values):
    logging.info("Running validation against fs settings")
    if 'dir_name' not in values:
        logging.error("Validation failed")
        return False, "Validation failed key dir_name not found"
    return True, "Passed validation"

class FsSource(BaseSourceType):

    def __init__(self, env, settings = {}, writer = None):
        super().__init__(env, settings, writer)

        if not 'dir_name' in settings:
            logging.error("dir_name argument not provided under settings, exiting.")
            self.exit_on_failure({"errMessage" : "dir_name argument not provided under settings, exiting."})
        
        self.dir_name = self.settings['dir_name']
        
        self.partitions = self.__get_part()
        self.set_stop_callback(self.stop_callback_fn)
        self.set_pause_callback(self.pause_callback_fn)

        self.status['parts_assigned'] = self.partitions

        self.default_allowed_exts = ['jpg', 'jpeg', 'png']

        logging.info("Initialized fs source")

        self.frame_seq = 0

    def __get_part(self):

        def split(a, n):
            k, m = divmod(len(a), n)
            return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))
        
        try:
            
            if not os.path.exists(self.env.data_path) :
                logging.error("Path {} not mounted to the pod, exiting since no frames to write".format(self.env.data_path))
                self.exit_on_failure({"errData" : "Path {} not mounted to the pod, exiting since no frames to write".format(self.env.data_path)})
            
            dir_path = os.path.join(self.env.data_path, self.dir_name)
            if not os.path.exists(dir_path):
                logging.error("Directory {} does not exist.".format(dir_path))
                self.exit_on_failure({"errData" : "Directory {} does not exist.".format(dir_path)})
            
            #load all the sub-directories present:
            sub_dirs = os.listdir(dir_path)

            #split across k-parts
            parts = list(split(sub_dirs, int(self.env.n_workers)))

            #get the current index of the worker:
            current_worker_index = int(self.env.worker_index)
            if current_worker_index > ( len(parts) - 1 ):
                logging.info("Worker with index {} is not required because it has no work".format(current_worker_index))
                self.exit_on_success(self.status)
            

            #get the partition which belongs to this worker:
            self_partition = parts[current_worker_index]
            if len(self_partition) == 0 :
                logging.info("Worker with index {} has no partition assigned. So it is not required".format(current_worker_index))
                self.exit_on_success({"errData" : "Worker is not required, It was not assigned any partitions"})

            for part in self_partition:
                part_path = os.path.join(dir_path, part)
                if not os.path.isdir(part_path):
                    logging.error("Improper structure, all the sub-files under the root must be directories")
                    self.exit_on_failure({"errData" : "Improper structure, all the sub-files under the root must be directories"})
            
            part_paths = [os.path.join(self.dir_name, part) for part in self_partition]
            
            return part_paths
        
        except Exception as e:
            logging.error(e)
            logging.error("Failed to get prepare partition, exiting")
            self.exit_on_failure({"errData" : "Failed to get prepare partition, exiting"})
    

    def __generate_key(self, part_name, failure = False):

        part_key = "{}__fs__{}__{}".format(
            self.env.key_prefix,
            self.source_id,
            part_name
        )

        key_seq = None
        if failure:
            key_seq = self.frame_count - self.considered_frames
        else :
            key_seq = self.considered_frames
        
        if 'start_seq' in self.settings:
            key_seq += self.settings['start_seq']
        
        return "{}__{}".format(key_seq)
    
    def update_status(self, **kwargs):
        self.status['frames_produced'] = self.frame_count
        self.status['frames_written'] = self.considered_frames

        if kwargs['part_finished']:
            if 'processed_sub_parts' in self.status:
                self.status['processed_sub_parts'].append(kwargs['part'])
            else:
                self.status['processed_sub_parts'] = [kwargs['part']]
    
    def stop_callback_fn(self, event):
        logging.info("Stop event detected")
        self.has_stop_request = True

    def pause_callback_fn(self, event):
        logging.info("Pause event type detected")
        if event == "pause":
            self.is_paused = True
        else:
            self.is_paused = False
    
    def __load_part_metadata(self, file_path):
        return json.load(open(file_path))
    

    def __pause_lock(self):
        while self.is_paused:
            logging.info("Source is in paused state")
            time.sleep(5)

    def runner(self):
        
        #check if custom file extensions are provided:
        if 'extensions' in self.settings:
            self.default_allowed_exts = self.settings['extensions']
        
        for part in self.partitions:
            full_path = os.path.abspath(part)

            sub_part_has_metadata = False
            part_metadata_dict = {}

            metadata_path = os.path.join(full_path, "metadata.json")
            if not os.path.exists(full_path):
                continue

            #check if the part has metadata.json
            if os.path.exists(metadata_path):
                logging.info("Metdadata for path={} found at {}".format(
                    full_path, metadata_path
                ))

                part_metadata_dict = self.__load_part_metadata(metadata_path)
                sub_part_has_metadata = True
            
            #start reading frames:
            #read in sorted order, don't miss the sequence
            possible_frames_list = sorted(os.listdir(full_path)) 

            for frame in possible_frames_list:

                if self.has_stop_request:
                    return True, self.status

                self.__pause_lock()

                self.frame_seq +=1

                ext = frame.split(".")[-1]
                if ext not in self.default_allowed_exts:
                    logging.info("Discarding unknwon file : {}".format(frame))
                    continue
                #read the frame
                frame_fp = os.path.join(full_path, frame)
                if self.should_skip_frame():
                    continue
                
                frame_data = open(frame_fp, 'rb').read()
                should_validate = (self.env.enable_validation and sub_part_has_metadata)

                source_id = self.dir_name
                seq_number = self.get_frame_count(source_id)

                seq_number = seq_number + self.get_start_seq(source_id)

                self.update_frame_count(source_id)

                metadata = {
                    "seq_no" : self.frame_count,
                    "part" : part,
                    "image_name" : frame,
                    "ext" : ext,
                    "size" : len(frame_data),
                    "task" : "fs",
                    "source_id" : self.dir_name,
                    "frame_seq_number" : self.frame_seq
                }

                if should_validate and (not self.is_valid_frame(part_metadata_dict)):
                    #frame did not pass validation, save it to corrupt table
                    if self.env.enable_corrupt_persistence:
                        self.write_failure_frame(
                            self.__generate_key(part, failure = True),
                            frame_data,
                            metadata,
                            part_metadata_dict
                        )

                    self.frame_seq +=1
                    continue
                
                self.mark_frame_as_proper()
                self.write_success_frame(
                    self.__generate_key(part, failure = False),
                    frame_data,
                    metadata,
                    part_metadata_dict
                )

                self.update_status(part_finished = False)

                self.frame_seq +=1

                #check frame limit
                if self.env.frame_limit != -1 and self.frame_count >= self.env.frame_limit:

                    if self.env.enable_batch_pause:
                        self.is_paused = True
                        logging.info("Stopped after writing {} frames.".format(self.env.frame_limit))

                    else:
                        return True, self.status
            else:
                self.update_status(part_finished = True, part = part)
        
        return True, self.status

    def run(self):

        try:

            ret, stats = self.runner()
            return ret, stats

        except Exception as e:
            logging.error(e)
            return False, str(e)