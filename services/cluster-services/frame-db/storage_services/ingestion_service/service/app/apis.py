from .k8s import K8sApi
from fastapi import APIRouter, Request
from .utils import with_logging, validate_json_fields, send_error_message, send_success_message

import logging
logging = logging.getLogger("MainLogger")


def log_request(request: Request, dictPayload: dict = None):

    url = request.url.path
    logging.info(
        "{} got hit".format(url),
        extra={
            "client_host": request.client.host,
            "client_port": request.client.port,
            "payload": str(dictPayload) if dictPayload else None,
            "endpoint": url
        }
    )


def __validate_and_send_result(ret: bool, result):
    return send_success_message(result) if ret else send_error_message(result)


class IngestionsJobsController:

    @staticmethod
    def CreateIngestionJob(job_name, type_="adhoc", parameters={}):
        try:

            if type_ == "adhoc":
                k8sClient = K8sApi.GetBatchApi()
                parameters['name'] = job_name
                ret, result = K8sApi.CreateIngestionJob(k8sClient, parameters)
                if not ret:
                    logging.error(result)
                    return False, str(result)
                return True, result

            if type_ == "scheduled":
                k8sClient = K8sApi.GetBatchBetaApi()
                parameters['name'] = job_name
                ret, result = K8sApi.CreateIngestionSchedule(
                    k8sClient, parameters)
                if not ret:
                    logging.error(result)
                    return False, str(result)
                return True, result

            return False, "Invalid job type {}, supported types are [adhoc, scheduled]".format(type_)
        except Exception as e:
            logging.error(e)
            return False, str(e)

    @staticmethod
    def ListIngestionJobs(type_="adhoc", parameters={}):
        try:

            if type_ == "adhoc":
                k8sClient = K8sApi.GetBatchApi()
                ret, result = K8sApi.ListIngestionJobs(k8sClient, parameters)
                if not ret:
                    logging.error(result)
                    return False, str(result)
                return True, result

            if type_ == "scheduled":
                k8sClient = K8sApi.GetBatchBetaApi()
                ret, result = K8sApi.ListIngestionSchedules(
                    k8sClient, parameters)
                if not ret:
                    logging.error(result)
                    return False, str(result)
                return True, result

            return False, "Invalid job type {}, supported types are [adhoc, scheduled]".format(type_)

        except Exception as e:
            logging.error(e)
            return False, str(e)

    @staticmethod
    def DeleteIngestionJob(job_name, type_="adhoc", parameters={}):

        try:

            if type_ == "adhoc":
                k8sClient = K8sApi.GetBatchApi()
                parameters['name'] = job_name
                ret, result = K8sApi.DeleteIngestionJob(k8sClient, parameters)
                if not ret:
                    logging.error(result)
                    return False, str(result)
                return True, result

            if type_ == "scheduled":
                k8sClient = K8sApi.GetBatchBetaApi()
                parameters['name'] = job_name
                ret, result = K8sApi.DeleteIngestionSchedules(
                    k8sClient, parameters)
                if not ret:
                    logging.error(result)
                    return False, str(result)

                return True, result

            return False, "Invalid job type {}, supported types are [adhoc, scheduled]".format(type_)

        except Exception as e:
            logging.error(e)
            return False, str(e)


jobsRouter = APIRouter()


@with_logging("/jobs/listJobs")
@jobsRouter.post("/listJobs")
async def listJobs(body: dict, request: Request):
    log_request(request, body)

    ret, field = validate_json_fields(body, ['jobType'])
    if not ret:
        return send_error_message("Missing field " + field)

    ret, result = IngestionsJobsController.ListIngestionJobs(
        body['jobType'], body['parameters'] if 'parameters' in body else {})
    print(type(result))
    return __validate_and_send_result(ret, result)


@with_logging("/jobs/deleteJob")
@jobsRouter.post("/deleteJob")
async def deleteJob(body: dict, request: Request):
    log_request(request, body)

    ret, field = validate_json_fields(body, ['jobName', 'jobType'])
    if not ret:
        return send_error_message("Missing field " + field)

    ret, result = IngestionsJobsController.DeleteIngestionJob(
        body['jobName'], body['jobType'])
    return __validate_and_send_result(ret, result)


@with_logging("/jobs/createJob")
@jobsRouter.post("/createJob")
async def createJob(body: dict, request: Request):
    log_request(request, body)

    ret, field = validate_json_fields(
        body, ['jobName', 'jobType', 'jobParameters'])
    if not ret:
        return send_error_message("Missing field " + jobName)

    ret, result = IngestionsJobsController.CreateIngestionJob(
        body['jobName'],
        body['jobType'],
        body['jobParameters']
    )

    return __validate_and_send_result(ret, result)
