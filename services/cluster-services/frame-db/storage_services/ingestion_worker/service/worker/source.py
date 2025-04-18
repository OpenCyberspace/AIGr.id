from .env import get_env_settings, exit_on_success, exit_on_failure
from .completion_notify import wrap_notify_failure, wrap_notify_success
from .connector import FrameWriter
import json

import logging
logging = logging.getLogger("MainLogger")

from .sources import sources_list


env_settings = get_env_settings()

ERR_NO_SOURCE = "NoSuchSourceException"
ERR_NO_VALIDATION = "SourceValidationFailed"
ERR_TASK_RUN_FAILED = "TaskFailedToRun"


def parse_settings_as_dict(source_type : str, settings : str, validator = None):

    try:
        logging.info("Parsing source settings : Type={} Settings={}".format(source_type, settings))

        settings = json.loads(settings.source_data)
        if validator:
            ret, errorMessage = validator(settings)
            if not ret:
                logging.error(errorMessage)
                wrap_notify_failure({"errMessage" : errorMessage})
                exit_on_failure()

        logging.info("Parsing settings complete Type={} settings={}".format(source_type, settings))
        return True, settings

    except Exception as e:

        err_msg = "Parse failed, Settings is not a valid JSON encoded string"

        logging.error(err_msg)
        logging.error(e)

        wrap_notify_failure({"errMessage" : err_msg})

        return False, str(e)

class Source:

    #source is responsible init the source and generate frames,
    #it checks the source 
    #it can implement methods like pause(), finish() and exit()
    #it also implements metrics_callback and also other callbacks

    def __init__(self, source_type, callbacks_dict = {}):
        self.source_type = source_type

        source_class, validator = self.__validate_source_exist()

        ret, settings = parse_settings_as_dict(self.source_type, env_settings, validator)
        if not ret :
            self.__default_exit_on_error(ERR_NO_VALIDATION, "Validation failed improper settings string")
        
        #everything okay! create the instance of the class
        
        self.writer = FrameWriter()

        self.source = source_class(env_settings, settings, self.writer)
        self.settings = settings

        self.pasue_queue = self.source.pasue_queue
        self.stop_queue = self.source.stop_queue
    

    def __default_exit_on_error(self, e, message):
        logging.error(message)
        logging.error(e)

        wrap_notify_failure({"errData" : message, "python_exception" : str(e)})

        exit_on_failure()
    

    def __validate_source_exist(self):
        try:
            if self.source_type not in sources_list :
                self.__default_exit_on_error(ERR_NO_SOURCE, "Source type {} not found".format(self.source_type))
            
            #get the source type:
            source_impl = sources_list[self.source_type]
            source_class = source_impl[0]
            if not source_class :
                self.__default_exit_on_error(ERR_NO_SOURCE, "Source type {} is not yet implemented".format(self.source_type))

            validator = None

            #check if there is a validator that validates the settings provided
            if source_impl[1]:
                validator = source_impl[1]
            
            return source_class, validator
                 
        except Exception as e :
            self.__default_exit_on_error(e, "General exception")
    
    def run_task(self):
        try:

            #run the source, 
            ret, result = self.source.run()
            if not ret :
                return False, result
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    def pause(self):
        try:

            if self.pasue_queue :
                self.pasue_queue.put('pause')
            
        except Exception as e:
            logging.error("failed to pause the source")
            logging.error(e)
    
    def resume(self):
        try:

            if self.pasue_queue :
                self.pasue_queue.put('resume')
            
        except Exception as e:
            logging.error("failed to resume the source")
            logging.error(e)
    
    def stop(self):

        try:

            success_data = self.stop()
            return True, success_data
            
        except Exception as e:
            logging.error(e)
            return False, str(e)