from .env import get_env_settings
import time
import redis
import logging 
import json

logging = logging.getLogger("MainLogger")

env_settings = get_env_settings()

class Pausers :

    @staticmethod
    def ListenForEvents():
        
        if not env_settings.enable_events:
            while True:
                time.sleep(100)
        
        #connect to redis and listen for events
        pub_sub_svc_params = env_settings.pub_sub_svc.split(":")
        pub_sub_password = env_settings.pub_sub_password

        #print(pub_sub_password)

        if len(pub_sub_svc_params) < 2:
            logging.error("invalid PUB_SUB_SVC given, it should be in the format = host:port")
            raise Exception("invalid PUB_SUB_SVC given, it should be in the format = host:port")

        host, port = pub_sub_svc_params
        logging.info("Trying to connect to Redis@{}:{}".format(host, port))
        
        #connect tosettings redis
        connection = None
        if env_settings.redis_cluster_mode:
            sentinel = redis.sentinel.Sentinel(
                [(host, port)], 
                sentinel_kwargs = {"password" : pub_sub_password}
            )

            master = sentinel.discover_master("mymaster")
            logging.info("Discovered redis master - mymaster : {}".format(master))

            master = master[0]
            
            connection = redis.Redis(
                host = master[0],
                port = master[1],
                db = 0,
                psasword = pub_sub_password
            )
        else :
            connection = redis.Redis(
                host = host,
                port = port,
                db = 0,
                password = pub_sub_password
            )
        
        #connect to the channel
        channel_name = "{}-{}_{}".format(
            env_settings.job_name,
            env_settings.worker_index,
            env_settings.sub_channel
        )

        #subscribe
        pubsub = connection.pubsub()
        pubsub.subscribe(channel_name)

        for item in pubsub.listen():

            print(item)
            
            #log ACK message to ensure successful channel creation
            if item['type'] == 'subscribe' and item['data'] == 1 :
                logging.info('Pubsub connection successful, listening for events')
            
            #filter noise
            if item['type'] == "message" and item['channel'].decode('utf-8') == channel_name:
                data = item['data']
                if type(data) == bytes:
                    data = json.loads(data.decode('utf-8'))
                
                yield data['action'].lower()