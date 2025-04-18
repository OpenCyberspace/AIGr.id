from fastapi import APIRouter, Request
import datetime
import logging
import time

from .configs import settings

logging = logging.getLogger("MainLogger")

from .utils import validate_json_fields, send_error_message, send_success_message,  with_logging
from  .db_api import DBApi

def __validate_result_and_send(ret, result) :
    return send_success_message(result) if ret else send_error_message(result)


def on_job_complete_callback(job_group, job_data):
    print('To be implemented.', job_group)


def log_request(request : Request, dictPayload : dict = None) :

    url = request.url.path
    logging.info(
        "{} got hit".format(url), 
        extra = {
            "client_host" : request.client.host,
            "client_port" : request.client.port,
            "payload" : str(dictPayload) if dictPayload else None,
            "endpoint" : url
        }
    )

class CompletedJobs:

    def __init__(self):

        #just using a dict instead of array to give O(1)'ness
        self.lock = False
    
    def markAsComplete(self, job_id, job_group, job_type, nWorkers, parameters = {}, status = "complete"):

        try:

            if not settings.PERSIST :
                return False, "Persistence is disabled"

            self.lock = True

            #mark job as complete based on its type:
            if job_type == "adhoc" :
                print(parameters)
                ret, result = DBApi.UpdateAdhoc(job_id, job_group, parameters = parameters, status =  status)
                if not ret :
                    self.lock = False
                    return False, str(result)
                
                self.lock = False
                return True, result
            
            if job_type == "scheduled" :

                ret, result = DBApi.UpdateCountScheduled(job_id, job_group, parameters = parameters, status = status)
                if not ret :
                    self.lock = False
                    return False, str(result)
                
                self.lock = False
                return True, result

            self.lock = False
            return False, "Invalid job type - {}, supported types are [adhoc, scheduled]".format(job_type)

        except Exception as e :
            logging.error(e)
            self.lock = False
            return False, str(e)
    

    def getStatus(self, job_group, job_type = "adhoc"):

        if not settings.PERSIST:
            return False, "Persistence is disabled"

        lock_idx = 0
        while self.lock :
            time.sleep(1/1000)
            lock_idx +=1

            if lock_idx >= 1000:
                break

        ret, result = DBApi.ListJobs({"job_group_name" : job_group, "job_type" : job_type})
        if not ret :
            return False, str(result)
    
        
        return True, {"jobName" : job_group, "jobType" : job_type, "jobWorkers" : result}
    

    def getStatusBoard(self):

        if not settings.PERSIST:
            return False, "Persistence is disabled"

        lock_idx = 0
        while self.lock :
            time.sleep(1/1000)
            lock_idx +=1
            if lock_idx >= 1000:
                break

        ret, result = DBApi.GetStatusBoard()
        if not ret :
            return False, str(result)
            
        return True, result

completionRouter = APIRouter()
jobs = CompletedJobs()

@with_logging("/completedJobs/getStatusBoard")
@completionRouter.get("/getStatusBoard")
async def getStatusBoard(request : Request):

    log_request(request, {})
    ret, result = jobs.getStatusBoard()
    return __validate_result_and_send(ret, result)

@with_logging("/completedJobs/getJobStatus")
@completionRouter.post("/getJobStatus")
async def getJobStatus(body : dict, request : Request):

    log_request(request, body)

    ret, field = validate_json_fields(body, ['jobName', 'jobType'])
    if not ret :
        return send_error_message("Missing field " + field)

    ret, result = jobs.getStatus(body['jobName'], body['jobType'])
    return __validate_result_and_send(ret, result)

@with_logging("/completedJobs/markAsComplete")
@completionRouter.post("/markAsComplete")
async def markAsComplete(body : dict, request : Request):

    log_request(request, body)

    ret, field = validate_json_fields(body, ['jobName', 'jobId', 'nWorkers', 'jobType', 'parameters'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = jobs.markAsComplete(body['jobId'], body['jobName'], body['jobType'], body['nWorkers'], body['parameters'], "complete")
    return __validate_result_and_send(ret, result)


@with_logging("/completedJobs/markAsFailed")
@completionRouter.post("/markAsFailed")
async def markAsFailed(body : dict, request : Request):

    log_request(request, body)

    ret, field = validate_json_fields(body, ['jobName', 'jobId', 'nWorkers', 'jobType', 'parameters'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = jobs.markAsComplete(body['jobId'], body['jobName'], body['jobType'], body['nWorkers'], body['parameters'], "failed")
    return __validate_result_and_send(ret, result)