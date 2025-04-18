import logging
from datetime import datetime
logging = logging.getLogger("MainLogger")


#A wrapper function for logging API requests
def with_logging(api_name) :
    def logging_wrapper(function) :
        def logging_internal(*args, **kwargs) :
            timestamp = datetime.now()
            logger.info("API {} got hit {}".format(), extra = {
                "api_name" : api_name,
                "time" : timestamp
            })

            return function(*args, **kwargs)
        return logging_internal
    return logging_wrapper


def validate_json_fields(data, fields) :
    for field in fields :
        if not field in data :
            return False, field
    return True, None

def send_success_message(data) :
    return {"success" : True, "result" : data}

def send_error_message(data) :
    return {"success" : False, "errorData" : data}