from .env import get_env_settings
import json
import logging

logging = logging.getLogger("MainLogger")

from .writer import FrameWriter
from .validator import FrameValidator

env = get_env_settings()
settings = env.source_data


def default_validation_function(self, validtion_data, frame_metadata):

    for key in validtion_data:
        if key in frame_metadata:
            if  frame_metadata[key] != validtion_data[key]:
                logging.error("Validation failed, expected {}={}, got {}".format(key, validtion_data[key], frame_metadata[key]))
                return False
    
    return True

class GstreamerSource :

    def __init__(self, source_id:str, validation_function = None):

        self.frame_writer = FrameWriter()

        self.settings_json = json.loads(settings)
        self.source_id = source_id
        self.start_seq = self.frame_writer.get_last_seq(self.source_id)

        validation_function = validation_function if validation_function else default_validation_function

        self.validator_class = FrameValidator(validator_rule_fn = validation_function, use_own_keys = False)
        logging.info("Init: Plugin::GstreamerSource complete")

        self.frame_seq = 0
        self.validation_metadata = self.settings_json['validations'] if 'validations' in self.settings_json else {}

        self.frame_writer = FrameWriter()
    

    def generate_key(self):

        key = "{}__gst__{}__{}".format(
            env.key_prefix,
            self.source_id,
            env.worker_index
        )

        seq = self.start_seq + self.frame_seq

        return "{}__{}".format(key,seq)
    
    def write_frame(self, frame, validation_data = {}):
        
        try:

            frame_metadata = {
                "seq_no" : self.frame_seq,
                "part" : "gst",
                "size" : len(frame),
                "ext" : "jpg",
                "task" : "gstreamer",
                "source_id" : self.source_id,
                "frame_seq_number" : self.frame_seq + self.start_seq
            }

            should_validate = validation_data != {} and env.enable_validation        
            if should_validate and not self.validator_class.is_valid_frame(None, None, self.validation_metadata, validation_data):
                logging.info("Frame {} did not pass validation".format(self.frame_seq))
                if env.enable_corrupt_persistence:
                    key = self.generate_key()
                    self.frame_writer.insert_to_corrupt_frames(
                        key, frame, frame_metadata,validation_data  
                    )

                self.frame_seq +=1
                return True, "Wrote frame"

            #passed validation
            key = self.generate_key()
            self.frame_writer.insert_to_frames(
                key,
                frame,
                frame_metadata,
                validation_data
            )

            self.start_seq +=1
            return True, "Wrote frame"

        except Exception as e:
            logging.error(e)
            return False, str(e)            

