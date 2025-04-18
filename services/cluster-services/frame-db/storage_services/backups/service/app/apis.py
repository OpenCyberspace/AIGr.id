from .configs import settings
settings.load_settings()

from .utils import with_logging, send_error_message, send_success_message, validate_json_fields
from .k8s import K8sApi

from fastapi import APIRouter, Request

import logging
logging = logging.getLogger("MainLogger")

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

class BackupController:

    @staticmethod
    def GetBackupInfo(type_ = "adhoc") :
        try:

            if type_ == "adhoc" :
                k8sclient = K8sApi.GetCustomObjectsApi()
                backupObjects = K8sApi.GetBackupObjects(k8sclient)
                return True, backupObjects
            
            if type_ == "scheduled" :
                k8sclient = K8sApi.GetCustomObjectsApi()
                backupObjects = K8sApi.GetScheduledBackupObjects(k8sclient)
                return True, backupObjects

            
            return False, "Invalid type {} supported types are [adhoc, scheduled]".format(type_)
            
        except Exception as e:
            logging.error(e)
            return False, str(e)

    @staticmethod
    def GetClusters() :

        try:

            k8sClient = K8sApi.GetK8sApiClient()
        
            deployments = K8sApi.GetDeployments(k8sClient)

            formatted_output = []

            for deployment in deployments :
                #print(deployment.metadata.labels['app.kubernetes.io/instance'])
                labels = deployment.metadata.labels
                if 'app.kubernetes.io/instance' in labels :
                    formatted_output.append(labels['app.kubernetes.io/instance'])

            return True, formatted_output

        except Exception as e :
            logging.error(e)
            return False, str(e)
        

    @staticmethod
    def UpdateBackupSchedule(clusterName : str, yamlInfo : dict):
        try:

            k8sClient = K8sApi.GetCustomObjectsApi()
            ret, result = K8sApi.CreateOrUpdateScheuledObject(k8sClient, clusterName, yamlInfo)

            if not ret :
                return False, str(result)

            return ret, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)


    @staticmethod
    def CreateInstantBackup(clusterName : str, yamlInfo : dict):

        try:

            k8sClient = K8sApi.GetCustomObjectsApi()
            ret, result = K8sApi.CreateBackupObject(
                k8sClient, clusterName,yamlInfo
            )

            if not ret :
                return False, str(result)
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e) 
    

    @staticmethod
    def RemoveBackupObject(backupName : str, type_ : str):

        try:
            if type_ == "adhoc" :

                k8sclient = K8sApi.GetCustomObjectsApi()
                ret, result = K8sApi.RemoveBackup(k8sclient, backupName)
                return True, result
            
            if type_ == "scheduled" : 

                k8sclient = K8sApi.GetCustomObjectsApi()
                ret, result = K8sApi.RemovebackupSchedule(k8sclient, backupName) 
                return True, result
            
            return "Invalid type {}, supported types are [adhoc, scheduled]".format(type_)

        except Exception as e :
            logging.error(e)
            return False, str(e)

class RestoreController :

    @staticmethod
    def CreateRestore(clusterName : str, yamlInfo : dict):
        
        try:

            k8sClient = K8sApi.GetCustomObjectsApi()
            ret, result = K8sApi.CreateRestore(
                k8sClient, clusterName, yamlInfo
            )

            if not ret :
                return False, str(result)
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def ListRestores() :

        try:

            k8sclient = K8sApi.GetCustomObjectsApi()
            ret, result = K8sApi.ListRestores(k8sclient)
            if not ret :
                return False, "Failed to list restore objects"
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)

    
    @staticmethod
    def DeleteRestore(restoreName: str):
        
        try:

            k8sClient = K8sApi.GetCustomObjectsApi()
            ret, result = K8sApi.RemoveRestore(
                k8sClient, restoreName
            )

            if not ret :
                return False, str(result)
            
            return True, result
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    





backupsRouter = APIRouter()

@with_logging("/backup/getBackupInfo")
@backupsRouter.post("/getBackupInfo")
async def getBackupInfo(body : dict, request : Request):

    log_request(request, body)
    ret, fieldName = validate_json_fields(body, ['backupType'])
    if not ret :
        return send_error_message("Missing field " + fieldName)
    
    ret, result = BackupController.GetBackupInfo(body['backupType'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/backup/deleteBackup")
@backupsRouter.post("/deleteBackup")
async def deleteBackupInfo(body : dict, request : Request):

    log_request(request, body)
    ret, fieldName = validate_json_fields(body, ['backupType', 'backupName'])
    if not ret :
        return send_error_message("Missing field " + fieldName)
    
    ret, result = BackupController.RemoveBackupObject(body['backupName'], body['backupType'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/backup/getClusters")
@backupsRouter.get("/getClusters")
async def getClusters(request : Request):

    log_request(request, {})
    ret, result = BackupController.GetClusters()
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/backup/updateSchedule")
@backupsRouter.post("/updateSchedule")
async def updateSchedule(body : dict, request : Request):

    log_request(request, body)
    ret, fieldName = validate_json_fields(body, ['clusterName', 'scheduleInfo'])
    if not ret :
        return send_error_message("Missing field " + fieldName)
    
    ret, result = BackupController.UpdateBackupSchedule(body['clusterName'], body['scheduleInfo'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/backup/createBackup")
@backupsRouter.post("/createBackup")
async def createBackup(body : dict, request : Request):

    log_request(request, body)
    ret, fieldName = validate_json_fields(body, ['clusterName', 'backupInfo'])
    if not ret :
        return send_error_message("Missing field " + fieldName)
    
    ret, result = BackupController.CreateInstantBackup(body['clusterName'], body['backupInfo'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/backup/restore")
@backupsRouter.post("/restore")
async def restore(body : dict, request : Request):

    log_request(request, body)
    ret, fieldName = validate_json_fields(body, ['clusterName', 'restoreInfo'])
    if not ret :
        return send_error_message("Missing field " + fieldName)
    
    ret, result = RestoreController.CreateRestore(body['clusterName'], body['restoreInfo'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


@with_logging("/backup/listRestores")
@backupsRouter.get("/listRestores")
async def list_restore(request : Request):

    log_request(request, {})
    
    ret, result = RestoreController.ListRestores()
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/backup/deleteRestore")
@backupsRouter.post("/deleteRestores")
async def delete_restores(body : dict, request : Request):

    log_request(request, body)

    ret, field = validate_json_fields(body, ['restoreName'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = RestoreController.DeleteRestore(body['restoreName'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)
