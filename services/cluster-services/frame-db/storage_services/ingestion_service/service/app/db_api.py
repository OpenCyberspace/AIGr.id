from pymodm import connect
from pymodm import MongoModel, EmbeddedDocumentField, EmbeddedDocumentListField, EmbeddedMongoModel
from pymodm import fields
import datetime

import logging
logging = logging.getLogger("MainLogger")

from .configs import settings

class JobsSchema(MongoModel):

    job_idx_name = fields.CharField(primary_key = True, required = True)
    job_group_name = fields.CharField(required = True)
    job_type = fields.CharField(required = True)  #adhoc/scheduled

    status = fields.CharField(required = True, default = "running")

    creation_time = fields.DateTimeField(required = True)
    last_job_complete_time = fields.DateTimeField(required = False, blank = True)

    job_env_parameters = fields.MongoBaseField(required = False, blank = True)
    job_completion_parameters = fields.MongoBaseField(required = False, blank = True)

    scheduled_node = fields.CharField(required = False, blank = True)
    jobs_completed = fields.IntegerField(required = False, default = 0)

    class Meta:
        final = True
        collection_name = "jobs_status"


class DBApi :

    @staticmethod
    def ConnectToDB():
        connect("{}/{}?authSource=admin".format(
            settings.MONGO_URI,
            settings.DB_NAME
        ))
    
    @staticmethod
    def AddJobs(job_data : list):

        try:

            DBApi.ConnectToDB()

            jobs_instances = []
            for instance in job_data :

                job_instance = JobsSchema(
                    job_idx_name = instance['job_idx_name'],
                    job_group_name = instance['job_group_name'],
                    job_type = instance['job_type'],
                    status = "running",
                    creation_time = datetime.datetime.now(),
                    job_env_parameters = instance['job_env_parameters'],
                    scheduled_node = instance['scheduled_node'],
                    jobs_completed = 0
                )

                job_instance.save()
            
            #bulk insert many records:
            #JobsSchema.objects.bulk_create(*jobs_instances)
            return True, "Saved records in mongodb"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)        
    
    @staticmethod
    def DeleteJobs(filters):

        try:

            print(filters)

            DBApi.ConnectToDB()
            JobsSchema.objects.raw(filters).delete()
            return True, "deleted db jobs"
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    

    @staticmethod
    def ListJobs(filters):
        
        try:

            DBApi.ConnectToDB()
            result = JobsSchema.objects.raw(filters).values()
            return True, list(result)
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def UpdateCountScheduled(job_name_idx, job_group, parameters = {"empty" : True}, status = "complete"):
        
        try:
            DBApi.ConnectToDB()
            result = JobsSchema.objects.get({"_id" : job_name_idx, "job_group_name" : job_group,  "job_type" : "scheduled"})
            if result :

                result.jobs_completed +=1
                result.last_job_complete_time = datetime.datetime.now()
                result.job_completion_parameters = parameters
                result.status = status
                result.save()
            
            return True, "Updated DB"

        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def UpdateAdhoc(job_name_idx, job_group_name, parameters, status):

        try:

            DBApi.ConnectToDB()
            result = JobsSchema.objects.get({"_id" : job_name_idx, "job_group_name" : job_group_name, "job_type" : "adhoc"})
            if result :
                result.jobs_completed = 1
                result.last_job_complete_time = datetime.datetime.now()
                result.job_completion_parameters = parameters
                result.status = status
                result.save()
            
            return True, "Updated DB"

        except Exception as e:
            logging.error(e)
            raise e
            return False, str(e)
    
    @staticmethod
    def GetStatusBoard():

        try:

            DBApi.ConnectToDB()

            objects = JobsSchema.objects.raw({}).values()
            objects = list(objects)

            return True, objects

        except Exception as e:
            logging.error(e)
            return False, str(e)