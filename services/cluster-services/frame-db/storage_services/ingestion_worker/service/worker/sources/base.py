import logging
import os 

logging = logging.getLogger("MainLogger")

from ..validator import FrameValidator
from ..pythreads import pythread
from queue import Queue
import time

from ..env import exit_on_success, exit_on_failure
from ..completion_notify import wrap_notify_failure, wrap_notify_success

from ..status import StatusPusher

class BaseSourceType :

    def __init__(self, env, settings = {}, writer = None):
        #store the settings
        self.env = env
        self.settings = settings
        
        #create queues for stop and pause/resume
        self.pasue_queue = Queue(20)
        self.stop_queue = Queue(20)

        #callback functions callbacks for queue events
        #the child class which extends this base class should set these variables
        #it should call set_pause_callback() and set_stop_callback()

        self.pause_callback = None
        self.stop_callback = None

        self.is_paused = False
        self.has_stop_request = False

        #status data
        self.status = {}

        #thread wrappers:
        self.pause_thread_handle = self.pause_thread(self)
        self.stop_thread_handle = self.stop_thread(self)

        #writer
        self.writer = writer

        #frame count - useful for implementing skip
        self.frame_count = 0
        self.considered_frames = 0

        self.source_id = self.settings['sourceId'] if 'sourceId' in self.settings else ""

        #check if skip is enabled
        self.skip_frame = self.settings['skip'] if 'skip' in self.settings else 0

        self.validator_class = None

        #for validation
        if env.enable_validation:
            self.validator_class = FrameValidator(
                validator_rule_fn = self.validation_function,
                use_own_keys = False
            )

            self.frame_requirements_metadata = self.settings['validations'] if 'validations' in self.settings else {}
        
       #status updater
        self.status_push_lock = False

        self.start_seq_cache = {}

        self.frame_counter_cache = {}
       
        #check if status notifications are enabled:
        if self.env.enable_status_publish:

            logging.info("Status updates are enabled, spawning status pusher thread")
            self.publish_status_updates(self)


    @pythread
    def pause_thread(self):
        while True:
            event = self.pasue_queue.get()
            if self.pause_callback :
                self.pause_callback(event)


    @pythread
    def stop_thread(self):
        while True:
            event = self.stop_queue.get()
            if self.stop_callback :
                self.stop_callback(event)
    

    def get_start_seq(self, source_id):
        if source_id not in self.start_seq_cache :
            seq_number = self.writer.get_last_seq(source_id)

            self.start_seq_cache[source_id] = seq_number

            return seq_number
        
        return self.start_seq_cache[source_id]


    @pythread
    def check_health(self):

        while True :
            try:
                time.sleep(120)
                if not self.pause_thread_handle.is_alive():
                    self.pause_thread_handle = self.pause_thread(self)
                    logging.warning("Pause thread had died, restarted")
                if not self.pause_thread_handle.is_alive():
                    self.stop_thread_handle = self.stop_thread(self)
                    logging.warning("Stop thread had died, restarted")
                
                logging.info("Source completed health-check")

            except Exception as e :
                logging.error(e)
                logging.error("Health check thread failed, restarting after 30 seconds")
                time.sleep(30)

    
    def set_pause_callback(self, callback):
        self.pause_callback = callback

    def set_stop_callback(self, callback):
        self.stop_callback = callback


    #completely implementable in child class
    def run(self, **kwargs):
        pass

    #completely implementable in child class
    def update_status(self, **kwargs):
        pass

    def mark_frame_as_proper(self):
        self.considered_frames +=1

    def get_status(self):
        return self.status
    
    def write_frame(self, key, frame_data):
        logging.warning("[write_frame] To be implemented")
    
    def should_skip_frame(self):
        should_skip = True
        self.frame_count +=1

        if self.skip_frame == 0 :
            return False

        if self.skip_frame != 0 and ( self.frame_count % self.skip_frame == 0 ):
            should_skip = False
        
        return should_skip
    
    def validation_function(self, metadata, frame_data):
        #implement this in child-class
        pass

    def is_valid_frame(self, frame_data):

        if not self.env.enable_validation:
            return True
        
        ret =  self.validator_class.is_valid_frame(None, None, self.frame_requirements_metadata, frame_data)
        if not ret :
            logging.warning("Frame with sequence {} did not pass validation".format(self.frame_count))
        
        return ret
    
    def passes_all_validations(self, frame, frame_meta):

        if self.should_skip_frame():
            return False, "skip"
        if self.is_valid_frame(frame_meta):
            return True, "validation"
        self.mark_as_improper()
        return False, "validation"
    
    def is_in_pause_state(self):
        return self.is_paused
    
    def write_success_frame(self, key : str, data : bytes, metadata : dict, frame_metadata : dict):
        self.writer.insert_to_frames(
            key,
            data, 
            metadata,
            frame_metadata
        )

    def write_failure_frame(self, key : str, data : bytes, metadata : dict, frame_metadata : dict):
        self.writer.insert_to_corrupt_frames(
            key,
            data,
            metadata,
            frame_metadata
        )
    
    def exit_on_success(self, exitData):
        wrap_notify_success(errData)
        exit_on_success()
    
    def exit_on_failure(self, exitData):
        wrap_notify_failure(exit_on_failure)
        exit_on_failure()
    
    @pythread
    def publish_status_updates(self) :

        while True:

            try:

                #init the connection
                pusher = StatusPusher()

                while True :

                    #push status every 10 seconds
                    time.sleep(self.env.status_push_interval)
                    logging.info("Pushing status update")

                    self.status_push_lock = True
                    pusher.publish(self.status)
                    self.status_push_lock = False
                
            except Exception as e:
                logging.error(e)
                logging.info("The publish thread caught an exception, respawning in next 30 seconds")
                self.status_push_lock = False

                time.sleep(30)

                continue
        
    def update_frame_count(self, source_id):
        if source_id in self.frame_counter_cache:
            self.frame_counter_cache[source_id] +=1
        else:
            self.frame_counter_cache[source_id] = 1
    
    def get_frame_count(self, source_id):

        return self.frame_counter_cache.get(source_id, 0)