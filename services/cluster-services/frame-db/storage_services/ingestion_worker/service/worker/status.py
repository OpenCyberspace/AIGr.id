import redis
import json

import logging
logging = logging.getLogger("MainLogger")

from .env import get_env_settings, exit_on_failure, exit_on_success
env_settings = get_env_settings()

PUB_QUEUE_NAME = "INGESTION_WORKER_STATUS"

class StatusPusher :

    def __init__(self):
        #created a redis connection
        self.connection = None

        try:

            conn_string = env_settings.pub_sub_svc
            conn_password = env_settings.pub_sub_password

            host, port = conn_string.split(":")

            if env_settings.redis_cluster_mode:
                sentinel = redis.sentinel.Sentinel(
                    [(host, int(port))],
                    sentinel_kwargs = {"password" : conn_password}
                )

                master = sentinel.discover_master("mymaster")[0]
                host, port = master

                self.connection = redis.Redis(
                    host = master,
                    port = port,
                    db = 0,
                    password = conn_password
                )
            else:

                #normal connection
                self.connection = redis.Redis(
                    host = host,
                    port = int(port),
                    db = 0,
                    password = conn_password
                )
            
        except Exception as e:
            logging.error(e)
            logging.error("Failed to create status pusher connection")

            #raise the exception, because the caller thread will handle it
            raise e
    

    def publish(self, data : dict):

        try:
            payload = {}

            print('pushing status : ', data)

            payload['worker_index'] = env_settings.worker_index
            payload['job_name'] = env_settings.job_name

            payload['status'] = data
            
            binary = json.dumps(payload).encode('utf-8')
            
            #publish
            self.connection.publish("framedb_job_status", binary)
        except Exception as e:
            logging.error(e)
            logging.error("Publish failed")
            #raise the exception, because the caller thread will handle it
            raise e

