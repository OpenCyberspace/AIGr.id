import logging
import logging.config
from pythonjsonlogger import jsonlogger
from datetime import datetime;

import os

class EfkJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(EfkJsonFormatter, self).add_fields(log_record, record, message_dict)
        #print(log_record.keys())
        log_record['ts'] = datetime.now().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['service_name'] = "framedb-storage.backup-service"
        


log_conf_path = os.path.join('app/log_config/logger.conf')
#print(log_conf_path)
logging.config.fileConfig(log_conf_path)