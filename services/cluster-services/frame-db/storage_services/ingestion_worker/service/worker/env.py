import os

sample_redis_settings = '''
    {
        "test" : true, 
        "skip" : 0, 
        "start_seq" : 100, 
        "host" : "localhost",  
        "port" : 6379, 
        "db" : 0, 
        "password" : "Friends123#", 
        "queue_prefix" : "test", 
        "queue_names" : ["1", "2", "3", "4", "5"], 
        "includes_meta" : true, 
        "size_padding" : 6
    }
'''

sample_kafka_settings = '''
{
    "test" : true,
    "skip" : 0,
    "start_seq" : 0,
    "host" : "127.0.0.1",
    "port" : 9092,
    "queue_prefix" : "test",
    "queue_names" : ["1", "2", "3"],
    "includes_meta" : true,
    "size_padding" : 6
}
'''

env_settings = [
    ('WORKER_INDEX', '0', int),
    ('N_WORKERS', '1', int),
    ('DESTINATION_NODE', "localhost:4000", str),
    ('JOB_TYPE', 'adhoc', str),
    ('KEY_PREFIX', 'test-frame', str),
    ('FRAME_LIMIT', '-1', int),
    ('SOURCE_TYPE', 'kafka', str),
    ('SOURCE_CONFIG_NAME', None, str),
    ('SOURCE_DATA', sample_kafka_settings, str),
    ('JOB_NAME', 'unknwon', str),
    ('ENABLE_NOTIFICATION', '1', int),
    ('INGESTION_URI', 'http://localhost:8000', str),
    ('PUB_SUB_SVC', 'localhost:6379', str),
    ('PUB_SUB_PASSWORD', None),
    ('ENABLE_VALIDATION', '0', int),
    ('ENABLE_CORRUPT_PERSISTENCE', '0', int),
    ('USE_CUSTOM_RULES', '0', int),
    ('CUSTOM_RULES_FILE', './rules.json', str),
    ('ENABLE_EVENTS', '1', int),
    ('REDIS_CLUSTER_MODE', '0', int),
    ('SUB_CHANNEL', '__actions', str),
    ('DB_CONNECTION_MODE', 'testing', str),
    ('DB_SETTINGS_USER', 'root'),
    ('DB_SETTINGS_PASSWORD', None),
    ('DB_NAME', "framedb"),
    ('DATA_PATH', "/frames"),
    ('ENABLE_STATUS_PUBLISH', '1', int),
    ('STATUS_PUSH_INTERVAL', '10', int),
    ('ENABLE_BATCH_PAUSE', '0', int)
]

class Settings:
    pass

def get_env_settings():

    settings = Settings()

    #get settings defined by ingestion-service
    for env_setting in env_settings:
        env_value = None
        if len(env_setting) == 2 :
            env_value = os.getenv(env_setting[0], env_setting[1])
        else:
            env_value = env_setting[2](os.getenv(env_setting[0], env_setting[1]))
        #print('loading env ', env_setting[0], env_value)
        setattr(settings, env_setting[0].lower(), env_value)
    
    return settings

def exit_on_failure():
    os._exit(0)

def exit_on_success():
    os._exit(0)
