import logging
import json
import os 
from .env import get_env_settings

env_settings = get_env_settings()


ENABLE_CORRUPT_PERSISTENCE = env_settings.enable_corrupt_persistence

USE_CUSTOM_RULES = True if os.getenv("USE_CUSTOM_RULES", "No").lower() == "yes" else False
CUSTOM_RULES_FILE = os.getenv("RULE_FILE", "./rules.json")


class FrameValidator :

    def __init__(self, validator_rule_fn = None, use_own_keys = False) :

        self.validator_rule_fn = validator_rule_fn
        
        self.use_own_keys = use_own_keys
        if self.use_own_keys :
            self.last_known_idx = 0
        
        if USE_CUSTOM_RULES :
            if not os.path.exists(CUSTOM_RULES_FILE) :
                logging.error("Rules file " + CUSTOM_RULES_FILE + " not found")
                os._exit(0)
            
            self.custom_rules = json.load(open(CUSTOM_RULES_FILE))
            print('Loaded rule file ', self.custom_rules)
    

    def is_valid_frame(self, key = None, data = None, metadata = {}, frame_data = None) :

        ret = True 

        if USE_CUSTOM_RULES :
            ret = self.custom_rules_matcher(
                metadata if not USE_CUSTOM_RULES else self.custom_rules,
                frame_data
            )

        else :
            ret = self.validator_rule_fn(
                metadata if not USE_CUSTOM_RULES else self.custom_rules,
                frame_data
            )
        
        return ret
    

    def custom_rules_matcher(self, custom_rules : dict, frame_caps : dict) :

        #match rules by checking for equality
        for cap_name in self.custom_rules :
            if cap_name not in frame_caps:
                continue
            if frame_caps[cap_name] != self.custom_rules[cap_name] :
                return False
        else :
            return True

