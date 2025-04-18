from kubernetes import client, config
import yaml
import random
import json

from .db_api import DBApi

from .configs import settings
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


yaml_paths = {
    "job" : "templates/job.yaml",
    "schedule" : "templates/cron.yaml"
}


container_images = {
    "redis_kafka_fs" : "ingestion_worker:latest",
    "gstreamer" : "gstreamer_ingestion:latest"
}

cluster_settings = {
    "PUB_SUB_SVC" : "framedb-routing-pub-sub-redis.framedb-routing.svc.cluster.local",
    "PUB_SUB_PASSWORD" :  {
        "valueFrom" : {
            "secretKeyRef": {
                "name" : "routing-pubsub-creds",
                "key" : "password"
            }
        }
    },
    "ENABLE_STATUS_PUSH" : '1',
    "STATUS_PUSH_INTERVAL" : '10',
    "ENABLE_CORRUPT_PERSISTENCE" : '1',
    "ENABLE_VALIDATION" : '1',
    "REDIS_CLUSTER_MODE" : '1',
    "DB_SETTINGS_USER" : "root",
    "DB_SETTINGS_PASSWORD" : "Friends123",
    "INGESTION_URI" : "http://ingestion-service-svc.framedb-storage.svc.cluster.local:8000"
}
 
class JobProcessors :

    @staticmethod
    def ChooseContainerImage(jobType:str, configPayload:dict, type_ = 'sched'):
        if jobType != "gstreamer":
            if type_ == 'sched':
                 configPayload['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['name'] = 'ingestion'
                 configPayload['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['image'] = container_images['redis_kafka_fs']
            else:
                configPayload['spec']['template']['spec']['containers'][0]['image'] = 'ingestion'
                configPayload['spec']['template']['spec']['containers'][0]['image'] = container_images['redis_kafka_fs']
        else:
            if type_ == "sched":
                configPayload['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['name'] = 'gstreamer'
                configPayload['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['image'] = container_images['gstreamer']
            else:
                configPayload['spec']['template']['spec']['containers'][0]['name'] = 'gstreamer'
                configPayload['spec']['template']['spec']['containers'][0]['image'] = container_images['gstreamer']
        

        logging.info("Job metadata " + json.dumps(configPayload))
        
        return configPayload

    @staticmethod
    def ProcessJob(parameters):
        #takes dict parameters, loads the yaml template
        #process and sets the parameters and then returns the processed yaml as dict

        job_template = yaml.safe_load(open(yaml_paths['job']))
        job_template['metadata']['name'] = parameters['job_idx_name']

        selected_node = None

        if 'node' in parameters :
            node_sel = parameters['node']
            if type(parameters['node']) == list:
                node_sel = random.choice(parameters['node'])

            job_template['metadata']['labels']['jobNode'] = node_sel
            job_template['spec']['template']['spec']['nodeSelector'] = {
                "framedb" : node_sel
            }

            selected_node = node_sel
        
        job_template['metadata']['labels']['jobGroup'] = parameters['name']

        #set env variables if exists
        if 'env' in parameters and type(parameters['env']) == dict :

            envs_array = []
            for env_name, env_value in parameters['env'].items():
                envs_array.append({
                    "name" : env_name,
                    "value" : str(env_value)
                })
                
            job_template['spec']['template']['spec']['containers'][0]['env'] = envs_array
        
            job_template = JobProcessors.ChooseContainerImage(parameters['env']['SOURCE_TYPE'], job_template, type_ = "adhoc")

        return job_template, selected_node if selected_node else 'unbounded'
    
    @staticmethod
    def ProcessSchedule(parameters):
        #takes dict parameters, loads the yaml template
        #process and sets the parameters and then returns the processed yaml as dict

        job_template = yaml.safe_load(open(yaml_paths['schedule']))
        job_template['metadata']['name'] = parameters['job_idx_name']
        job_template['spec']['schedule'] = parameters['schedule']

        selected_node = None

        if 'node' in parameters :
            node_sel = parameters['node']
            if type(parameters['node']) == list:
                node_sel = random.choice(parameters['node'])

            job_template['metadata']['labels']['jobNode'] = node_sel
            job_template['spec']['jobTemplate']['spec']['template']['spec']['nodeSelector'] = {
                "framedb" : node_sel
            }

            selected_node = node_sel
        
        if 'env' in parameters and type(parameters['env']) == dict :
            envs_array = []
            for env_name, env_value in parameters['env'].items():
                envs_array.append({
                    "name" : env_name,
                    "value" :  str(env_value) 
                })

            job_template['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]['env'] = envs_array
            job_template = JobProcessors.ChooseContainerImage(parameters['env']['SOURCE_TYPE'], job_template, type_ = "sched")
        
        job_template['metadata']['labels']['jobGroup'] = parameters['name']
        
        return job_template, selected_node if selected_node else 'unbounded'

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
    def GetBatchBetaApi() :
        config.load_kube_config()
        return client.BatchV1beta1Api()

    @staticmethod
    def GetBatchApi() :
        config.load_kube_config()
        return client.BatchV1Api()
    
    @staticmethod
    def _ProcessEnv(envData : dict, idx : int, nWorkers : int, job_type = "adhoc", job_name = "unknown"):
       
        env = {}
        #only one env is provided
        env['WORKER_INDEX'] = str(idx)
        env['N_WORKERS'] = str(nWorkers)
        env['DESTINATION_NODE'] = envData['destination']
        env['JOB_NAME'] = job_name

        env['JOB_TYPE'] = job_type

        if 'keyPrefix' in envData :
            env['KEY_PREFIX'] = envData['keyPrefix']
        
        if 'frameLimit' in envData :
            env['FRAME_LIMIT'] = envData['frameLimit']

        if 'sourceType' in envData :
            env['SOURCE_TYPE'] = envData['sourceType']
        
        if 'sourceConfigName' in envData :
            env['SOURCE_CONFIG_NAME'] = envData['sourceConfigName']
        elif 'sourceInfo' in envData :
            env['SOURCE_DATA'] = json.dumps(envData['sourceInfo'])
        else :
            return False, "Failed to process Env Data, provide either sourceConfigName or sourceInfo dict"

        #add other env variables that are behavioural settings:
        for setting in cluster_settings:
            env[setting] = cluster_settings[setting]

        return True, env
    

    @staticmethod
    def ProcessJob(jobData, job_idx_name, job_group, scheduled_node, job_type):
        
        job_dict = {
            "job_idx_name" : job_idx_name,
            "job_group_name" : job_group,
            "job_type" : job_type,
            "job_env_parameters" : jobData,
            "scheduled_node" : scheduled_node
        }

        return job_dict
    
    @staticmethod
    def PersistToDB(jobData):

        if not settings.PERSIST :
            return True, ""

        ret, result = DBApi.AddJobs(jobData)
        if not ret :
            logging.error(result)
            return False, "Persistance failed error - {}".format(result)
        return True, ""

    
    @staticmethod
    def CreateIngestionJob(client : client.BatchV1Api, batch_parameters : dict = {}):

        if not 'settings' in batch_parameters:
            return False, "Cannot create a job without settings."

        job_responses = []

        jobs_db = []

        if 'nWorkers' in batch_parameters and batch_parameters['nWorkers'] > 1 :
            for worker_idx in range(batch_parameters['nWorkers']) :
                job_name = batch_parameters['name'] + "-" + str(worker_idx)
                batch_parameters['job_idx_name'] = job_name

                if not 'settings' in batch_parameters :
                    return False, "Cannot create a job without settings."
                
                ret, env_data = K8sApi._ProcessEnv(batch_parameters['settings'], worker_idx, batch_parameters['nWorkers'], "adhoc", batch_parameters['name'])

                if not ret :
                    return False, str(env_data)

                batch_parameters['env'] = env_data

                body, node_scheduled = JobProcessors.ProcessJob(batch_parameters)

                db_job = K8sApi.ProcessJob(batch_parameters['settings'], job_name, batch_parameters['name'], node_scheduled, 'adhoc')
                jobs_db.append(db_job)

                response = client.create_namespaced_job(
                    namespace = "framedb-storage",
                    body = body
                )

                job_responses.append(response)

            
            ret, result = K8sApi.PersistToDB(jobs_db)
            if not ret :
                return False, result

            return True, job_responses
        
        #single job
        #process env variables with worker index = 0 and nWorkers = 1
        ret, env_data = K8sApi._ProcessEnv(batch_parameters['settings'], 0, 1, job_type="adhoc", job_name = batch_parameters['name'])
        if not ret :
            return False, str(env_data)

        batch_parameters['env'] = env_data

        job_idx_name = batch_parameters['name'] + "-0"

        batch_parameters['job_idx_name'] = job_idx_name
        body, node_scheduled = JobProcessors.ProcessJob(batch_parameters)

        #create db-insertable format of the job:
        db_job = K8sApi.ProcessJob(batch_parameters['settings'], job_idx_name, batch_parameters['name'], node_scheduled, "adhoc")
        jobs_db.append(db_job)

        response = client.create_namespaced_job(
            namespace = "framedb-storage",
            body = body
        )


        ret, result = K8sApi.PersistToDB(jobs_db)
        if not ret :
            return False, result

        return True, response

    @staticmethod
    def CreateIngestionSchedule(client : client.BatchV1beta1Api, batch_parameters : dict = {}):

        if not 'settings' in batch_parameters:
            return False, "Cannot create a job without settings."
        
        job_responses = []

        jobs_db = []

        if 'nWorkers' in batch_parameters and batch_parameters['nWorkers'] > 1 :
            for worker_idx in range(batch_parameters['nWorkers']) :
                job_name = batch_parameters['name'] + "-" + str(worker_idx)
                batch_parameters['job_idx_name'] = job_name

                ret, env_data = K8sApi._ProcessEnv(batch_parameters['settings'], worker_idx, batch_parameters['nWorkers'], "scheduled", batch_parameters['name'])

                if not ret :
                    return False, str(env_data)

                batch_parameters['env'] = env_data

                body, node_selected = JobProcessors.ProcessSchedule(batch_parameters)
                response = client.create_namespaced_cron_job(
                    namespace = "framedb-storage",
                    body = body
                )

                db_job = K8sApi.ProcessJob(batch_parameters['settings'], job_name, batch_parameters['name'], node_selected, "scheduled")
                jobs_db.append(db_job)

                job_responses.append(response)
            
            ret, result = DBApi.AddJobs(jobs_db)
            if not ret :
                return False, result

            return True, job_responses
        
        #single job
        ret, env_data = K8sApi._ProcessEnv(batch_parameters['settings'], 0, 1, job_type="scheduled", job_name =  batch_parameters['name'])
        if not ret :
            return False, str(env_data)

        batch_parameters['env'] = env_data

        job_idx_name = batch_parameters['name'] + "-0"

        batch_parameters['job_idx_name'] = batch_parameters['name'] + "-0"
        body, node_selected = JobProcessors.ProcessSchedule(batch_parameters)

        db_job = K8sApi.ProcessJob(batch_parameters['settings'], job_idx_name, batch_parameters['name'], node_selected, "scheduled")
        jobs_db.append(db_job)

        response = client.create_namespaced_cron_job(
            namespace = "framedb-storage",
            body = body
        )

        ret, result = DBApi.AddJobs(jobs_db)
        if not ret :
            return False, result

        return True, response

    @staticmethod
    def ListIngestionJobs(client : client.BatchV1Api, batch_parameters : dict = {}):

        #print(batch_parameters
        label_selector = None
        if 'node' in batch_parameters:
            label_selector = "jobNode="+batch_parameters['node']
        
        if 'jobName' in batch_parameters:
            if not label_selector :
                label_selector = "jobGroup="+batch_parameters['jobName']
            else:
                label_selector = label_selector + " , jobGroup="+batch_parameters['jobName']


        job_type_selector = "jobType=framedb-ingestion-job"
     
        jobsList = client.list_namespaced_job(
            namespace = "framedb-storage",
            label_selector = label_selector + " , {}".format(job_type_selector) if label_selector else job_type_selector
        )

        if type(jobsList) == str:
            return False, jobsList

        print(jobsList)

        return True, jobsList

    @staticmethod
    def ListIngestionSchedules(client: client.BatchV1beta1Api, batch_parameters : dict = {}):
        
        label_selector = None
        if 'node' in batch_parameters:
            label_selector = "jobNode="+batch_parameters['node']
        
        if 'jobName' in batch_parameters:
            if not label_selector :
                label_selector = "jobGroup="+batch_parameters['jobName']
            else:
                label_selector = label_selector + " , jobGroup="+batch_parameters['jobName']


        job_type_selector = "jobType=framedb-ingestion-schedule"
     
        jobsList = client.list_namespaced_cron_job(
            namespace = "framedb-storage",
            label_selector = label_selector + " , {}".format(job_type_selector) if label_selector else job_type_selector
        )

        if type(jobsList) == str:
            return False, jobsList

        return True, jobsList


    @staticmethod
    def DeleteIngestionJob(client : client.BatchV1Api, batch_parameters : dict = {}):

        labelSelector = None
        if 'node' in batch_parameters :
            labelSelector = "jobNode="+batch_parameters['node']
        
        if 'name' in batch_parameters :
            if not labelSelector :
                labelSelector = "jobGroup="+batch_parameters['name']
            else:
                labelSelector = labelSelector + " , jobGroup="
        
        job_type_selector = "jobType=framedb-ingestion-job"
        
        response = client.delete_collection_namespaced_job(
            namespace = "framedb-storage",
            label_selector = labelSelector + " , {}".format(job_type_selector) if labelSelector else job_type_selector
        )

        if type(response) == str:
            return False, response
        
        #remove from DB
        filters ={"job_group_name" : batch_parameters['name'], "job_type" : "adhoc"}
        if 'node' in batch_parameters :
            filters['scheduled_node'] = batch_parameters['node']

        if settings.PERSIST:
            ret, result = DBApi.DeleteJobs(filters)
            if not ret :
                return False, "Persistence failed error - {}".format(result)
        
        return True, response

    @staticmethod
    def DeleteIngestionSchedules(client : client.BatchV1beta1Api, batch_parameters : dict = {}):
        
        labelSelector = None
        if 'node' in batch_parameters :
            labelSelector = "jobNode="+batch_parameters['node']
        
        if 'name' in batch_parameters :
            if not labelSelector :
                labelSelector = "jobGroup="+batch_parameters['name']
            else:
                labelSelector = labelSelector + " , jobGroup="
        
        job_type_selector = "jobType=framedb-ingestion-schedule"
        
        response = client.delete_collection_namespaced_cron_job(
            namespace = "framedb-storage",
            label_selector = labelSelector + " , {}".format(job_type_selector) if labelSelector else job_type_selector 
        )

        if type(response) == str:
            return False, response
        
        filters ={"job_group_name" : batch_parameters['name'], "job_type" : "scheduled"}
        if 'node' in batch_parameters :
            filters['scheduled_node'] = batch_parameters['node']
        

        if settings.PERSIST :
            ret, result = DBApi.DeleteJobs(filters)
            if not ret :
                logging.error(result)
                return False, "Persistence failed error = {}".format(result)
        
        return True, response
