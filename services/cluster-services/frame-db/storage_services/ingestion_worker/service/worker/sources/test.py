from .base import BaseSourceType
import time
import os 
import logging

logging = logging.getLogger("MainLogger")

class TestSource(BaseSourceType):

    def __init__(self, env, settings, writer = None):
        super().__init__(env, settings, writer)

        self.set_pause_callback(self.pause_callback_fn)
        self.set_stop_callback(self.stop_callback_fn)

        #self.set_validation_function(self.validation_function)
    
    def update_status(self, **kwargs):
        self.status['frames_produced'] = self.frame_count
        self.status['frames_written'] = self.considered_frames
    
    def pause_callback_fn(self, event):

        #simple, since this is test source

        if event == 'pause':
            self.is_paused = True
        else:
            self.is_paused = False
    
    def stop_callback_fn(self, event):

        #simple, since this is test source 

        self.has_stop_request = True
    
    def validation_function(self, metadata, framedata):
        #the test source doesn't have validation function
        logging.warning("The test source does not implement any validation function")
        return True
    

    def generate_key(self, is_failure = False):

        key_prefix = self.env.key_prefix
        source_id = self.source_id

        key_seq = 0
        if is_failure:
            key_seq = self.frame_count - self.considered_frames
        else:
            key_seq = self.considered_frames

        if 'start_seq' in self.settings:
            key_seq += self.settings['start_seq']

        return "{}_{}_{}".format(self.env.key_prefix, self.source_id, key_seq)
    

    def run(self):
        #the actual run method, this is just a simulation since this is a test source
        data = os.urandom(10)
        while not self.has_stop_request :

            if self.has_stop_request:
                return True, self.status

            while self.is_in_pause_state():
                logging.info("Job is in paused state")
                time.sleep(10)
            
            logging.info("Generating frame, sequence = {}".format(self.frame_count))

            if self.should_skip_frame():
                continue
            
            #since validation functions is empty, we need not pass any frame metadata for test
            if not self.is_valid_frame({}):
                #validation failed, persist to DB
                if self.env.enable_corrupt_persistence:
                    self.write_failure_frame(
                        self.generate_key(is_failure = True),
                        data,
                        {"frame_seq_number" : self.frame_count, "size" : len(data)}
                    )
                continue

            self.mark_frame_as_proper()

            self.write_success_frame(
                self.generate_key(),
                data,
                {"frame_seq_number" : self.frame_count, "size" : len(data)}
            )

            logging.info("Total frames = {}, wrote frames = {}".format(self.frame_count, self.considered_frames))
            
            if self.env.frame_limit != -1 and self.considered_frames >= self.env.frame_limit:
                return True, self.status

            self.update_status()
            time.sleep(3)
        
        return True, self.status
    