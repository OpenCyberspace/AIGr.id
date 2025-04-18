import requests
from .env import get_env_settings

import logging
logging = logging.getLogger("MainLogger")

settings = get_env_settings()

class Routes :
    complete = "/completedJobs/markAsComplete",
    failed = "/completedJobs/markAsFailed"


class Notifier:

    @staticmethod
    def NotifyFailure(job_name, job_id, n_workers, job_type, parameters = {}):
        json_payload = {
            "jobName" : job_name,
            "jobId" : job_id,
            "nWorkers" : n_workers,
            "jobType" : job_type,
            "parameters" : parameters
        }

        try:
            URI = settings.ingestion_uri + Routes.failed
            logging.info("Notifying failure")
            response = requests.post(URI, json = json_payload).json()
            if response['success'] :
                logging.info(response)
            else:
                logging.error(response)
        except Exception as e:
            logging.error("Failed to notify job failure {}".format(e))
            return False, str(e)

    @staticmethod
    def NotifySuccess(job_name, job_id, n_workers, job_type, parameters = {}):
        json_payload = {
            "jobName" : job_name,
            "jobId" : job_id,
            "nWorkers" : n_workers,
            "jobType" : job_type,
            "parameters" : parameters
        }

        try:
            URI = settings.ingestion_uri + Routes.failed
            response = requests.post(URI, json = json_payload).json()
            logging.info("Notifying successful completion")
            if response['success'] :
                logging.info(response)
            else :
                logging.error(response)
        except Exception as e:
            logging.error("Failed to notify job success {}".format(e))
            return False, str(e)

def __get_settings():

    job_name = settings.job_name
    job_worker_index = settings.worker_index
    n_workers= settings.n_workers
    job_type = settings.job_type

    return [job_name, job_worker_index, n_workers, job_type] 

def wrap_notify_success(successData : dict):

    if not settings.enable_notification:
        logging.warning("Notifications not enabled")
        return
    #get the settings from env object
    params = __get_settings()
    params.append(successData)
    return Notifier.NotifySuccess(*params)
    

def wrap_notify_failure(errData : dict):

    if not settings.enable_notification:
        logging.warning("Notifications not enabled")
        return

    params = __get_settings()
    params.append(errData)
    return Notifier.NotifyFailure(*params)