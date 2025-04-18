import logging
import logging.config
from pythonjsonlogger import jsonlogger
from datetime import datetime;

import os

def get_env():
    job_name = os.getenv("JOB_NAME")
    worker_index = os.getenv('N_WORKERS')

    return job_name, worker_index



class EfkJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(EfkJsonFormatter, self).add_fields(log_record, record, message_dict)
        #print(log_record.keys())
        log_record['ts'] = datetime.now().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['service_name'] = "framedb-storage.ingestion-worker"
        
        #extra fields that adds job ID and job Name to enable filtering at Kibana
        job_params = get_env()

        log_record['job_index'] = job_params[1]
        log_record['job_group'] = job_params[0]


log_conf_path = os.path.join('app/log_config/logger.conf')
#print(log_conf_path)
logging.config.fileConfig(log_conf_path)