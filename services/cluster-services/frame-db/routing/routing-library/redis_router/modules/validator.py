import plyvel
from .corrupt_frames import CorruptFrameHandler
import logging
import json
import os 


ENABLE_CORRUPT_PERSISTENCE = True if os.getenv("ENABLE_CORRUPT_PERSISTENCE", "No").lower() == "yes" else False

USE_CUSTOM_RULES = True if os.getenv("USE_CUSTOM_RULES", "No").lower() == "yes" else False
CUSTOM_RULES_FILE = os.getenv("RULE_FILE", "./rules.json")


class FrameValidator :

    def __init__(self, sourceId, validator_rule_fn = None, use_own_keys = False) :

        self.sourceId = sourceId
        self.validator_rule_fn = validator_rule_fn
        
        if ENABLE_CORRUPT_PERSISTENCE :
            self.persist_db_handle = CorruptFrameHandler.create_handle(self.sourceId)
        
        self.use_own_keys = use_own_keys
        if self.use_own_keys :
            self.last_known_idx = 0
        
        if USE_CUSTOM_RULES :
            if not os.path.exists(CUSTOM_RULES_FILE) :
                logging.error("Rules file " + CUSTOM_RULES_FILE + " not found")
                os._exit(0)
            
            self.custom_rules = json.load(open(CUSTOM_RULES_FILE))
            print('Loaded rule file ', self.custom_rules)
    

    def is_valid_frame(self, key = None, data = None, routerObject = None, frame_data = None) :

        ret = True 

        if not self.validator_rule_fn :
            ret = self.custom_rules_matcher(
                routerObject.get_metadata() if not USE_CUSTOM_RULES else self.custom_rules,
                frame_data
            )

        else :
            ret = self.validator_rule_fn(
                routerObject.get_metadata() if not USE_CUSTOM_RULES else self.custom_rules,
                frame_data
            )

        if not ret :
            if ENABLE_CORRUPT_PERSISTENCE :

                if self.use_own_keys :
                    key = "{}__frame".format(self.last_known_idx)

                CorruptFrameHandler.write_frame_to_db(self.persist_db_handle, key, self.sourceId, data)

            logging.info("Invalid frame with key={} detected".format(
                key
            ))
            return False
        
        return True
    

    def custom_rules_matcher(self, custom_rules : dict, frame_caps : dict) :

        #match rules by checking for equality
        for cap_name in self.custom_rules :
            if frame_caps[cap_name] != self.custom_rules[cap_name] :
                return False
        else :
            return True

