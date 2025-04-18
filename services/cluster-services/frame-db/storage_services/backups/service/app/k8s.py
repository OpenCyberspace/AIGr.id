from kubernetes import client, config
import yaml

from .utils import validate_json_fields

import logging
logging = logging.getLogger("MainLogger")

def get_yaml(file_name) :

    try:
        yamlDict = yaml.safe_load(open(file_name))
        return True, yamlDict
    except Exception as e:
        logging.error(e)
        return False, str(e)


class K8sApi :

    @staticmethod
    def GetK8sApiClient() :
        config.load_kube_config()
        return client.AppsV1Api()
    
    @staticmethod
    def GetK8sCoreApi() :
        config.load_kube_config()
        return client.CoreV1Api()
    
    @staticmethod
    def GetCustomObjectsApi() :
        config.load_kube_config()
        return client.CustomObjectsApi()
    
    @staticmethod
    def GetDeployments(client : client.AppsV1Api) :
        deployments = client.list_namespaced_deployment(
            namespace = "framedb-storage-cluster",
            label_selector = "app.kubernetes.io/component=discovery"
        )

        return deployments.items
    
    @staticmethod
    def GetBackupObjects(client : client.CustomObjectsApi):
        backupObjects = client.list_namespaced_custom_object(
            group = "pingcap.com",
            version = "v1alpha1",
            namespace = "framedb-storage-cluster",
            plural = "backups"
        )

        return backupObjects['items']

    @staticmethod
    def GetScheduledBackupObjects(client : client.CustomObjectsApi):
        backupObjects = client.list_namespaced_custom_object(
            group = "pingcap.com",
            version = "v1alpha1",
            namespace = "framedb-storage-cluster",
            plural = "backupschedules"
        )

        return backupObjects['items']
    
    @staticmethod
    def CreateBackupObject(client : client.CustomObjectsApi, clusterName: str, yamlData : dict):

        #validate yamlData
        ret, field = validate_json_fields(yamlData, ['name', 'bucketName', 'bucketEndpoint'])
        if not ret :
            return False, "Missing field " + field + " in backup info"
        
        ret, dict_backup_obj = get_yaml('yamls/adhoc-template.yaml')
        if not ret :
            return False, str(dict_backup_obj)
        
        #set fields
        dict_backup_obj['metadata']['name'] = yamlData['name']
        dict_backup_obj['spec']['br']['cluster'] = clusterName
        dict_backup_obj['spec']['from']['host'] = clusterName + "-tidb.framedb-storage-cluster.svc.cluster.local"
        dict_backup_obj['spec']['s3']['endpoint'] = yamlData['bucketEndpoint']
        dict_backup_obj['spec']['s3']['bucket'] = yamlData['bucketName']
        dict_backup_obj['spec']['s3']['prefix'] = yamlData['name']

        #create the CRD
        response = client.create_namespaced_custom_object(
            group = 'pingcap.com',
            version = 'v1alpha1',
            namespace = 'framedb-storage-cluster',
            plural = "backups",
            body = dict_backup_obj
        )

        if type(response) == str :
            return True, response

        return True, "Created Backup for cluster " + clusterName + " as " + response['metadata']['name']


    @staticmethod
    def CreateOrUpdateScheuledObject(client : client.CustomObjectsApi, clusterName: str, yamlData : dict):

        #validate yamlData
        ret, field = validate_json_fields(yamlData, ['name', 'bucketName', 'bucketEndpoint', "schedule"])
        if not ret :
            return False, "Missing field " + field + " in backup info"
        
        ret, dict_backup_obj = get_yaml('yamls/scheduled-template.yaml')
        if not ret :
            return False, str(dict_backup_obj)
        
        #set fields
        dict_backup_obj['metadata']['name'] = yamlData['name']
        dict_backup_obj['spec']['backupTemplate']['br']['cluster'] = clusterName
        dict_backup_obj['spec']['backupTemplate']['from']['host'] = clusterName + "-tidb.framedb-storage-cluster.svc.cluster.local"
        dict_backup_obj['spec']['backupTemplate']['s3']['endpoint'] = yamlData['bucketEndpoint']
        dict_backup_obj['spec']['backupTemplate']['s3']['bucket'] = yamlData['bucketName']
        dict_backup_obj['spec']['backupTemplate']['s3']['prefix'] = yamlData['name']

        #set schedule
        dict_backup_obj['spec']['schedule'] = yamlData['schedule']

        #create the CRD
        response = client.create_namespaced_custom_object(
            group = 'pingcap.com',
            version = 'v1alpha1',
            namespace = 'framedb-storage-cluster',
            plural = "backupschedules",
            body = dict_backup_obj
        )

        if type(response) == str :
            return True, response

        return True, "Created backup schedule for cluster " + clusterName + " as " + response['metadata']['name']
     
        
    
    @staticmethod
    def CreateRestore(client : client.CustomObjectsApi, clusterName: str, yamlData : dict) :

        #validate yamlData
        ret, field = validate_json_fields(yamlData, ['name', 'bucketName', 'bucketEndpoint', 'backupName'])
        if not ret :
            return False, "Missing field " + field + " in backup info"
        
        ret, dict_backup_obj = get_yaml('yamls/restore-template.yaml')
        if not ret :
            return False, str(dict_backup_obj)
        
        #set fields
        dict_backup_obj['metadata']['name'] = yamlData['name']
        dict_backup_obj['spec']['br']['cluster'] = clusterName
        dict_backup_obj['spec']['to']['host'] = clusterName + "-tidb.framedb-storage-cluster.svc.cluster.local"
        dict_backup_obj['spec']['s3']['endpoint'] = yamlData['bucketEndpoint']
        dict_backup_obj['spec']['s3']['bucket'] = yamlData['bucketName']
        dict_backup_obj['spec']['s3']['prefix'] = yamlData['backupName']

        #create the CRD
        response = client.create_namespaced_custom_object(
            group = 'pingcap.com',
            version = 'v1alpha1',
            namespace = 'framedb-storage-cluster',
            plural = "restores",
            body = dict_backup_obj
        )

        if type(response) == str :
            return True, response

        return True, "Created Backup for cluster " + clusterName + " as " + response['metadata']['name']
    
    @staticmethod
    def RemoveRestore(client : client.CustomObjectsApi, restoreName : str) :

        response = client.delete_namespaced_custom_object(
            group = "pingcap.com",
            plural = "restores",
            version = "v1alpha1",
            namespace = "framedb-storage-cluster",
            name = restoreName
        ) 

        if type(response) == str :
            return True, response

        return True, response['status']
        
    @staticmethod
    def RemovebackupSchedule(client : client.CustomObjectsApi, backupName : str) :

        response = client.delete_namespaced_custom_object(
            group = "pingcap.com",
            plural = "backupschedules",
            version = "v1alpha1",
            namespace = "framedb-storage-cluster",
            name = backupName
        )

        if type(response) == str :
            return True, response

        return True, response['status']
    

    @staticmethod
    def RemoveBackup(client : client.CustomObjectsApi, backupName : str) :

        response = client.delete_namespaced_custom_object(
            group = "pingcap.com",
            plural = "backups",
            version = "v1alpha1",
            namespace = "framedb-storage-cluster",
            name = backupName
        )

        if type(response) == str :
            return True, response
        
        return True, response['status']
    
    @staticmethod
    def ListRestores(client : client.CustomObjectsApi) :

        response = client.list_namespaced_custom_object(
            group = "pingcap.com",
            version = "v1alpha1",
            plural = "restores",
            namespace = "framedb-storage-cluster"
        )

        if type(response) == str :
            return True, response
            
        return True, response['items']