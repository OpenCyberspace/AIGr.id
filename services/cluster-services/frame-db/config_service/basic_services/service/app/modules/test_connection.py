from redis import Redis

test_config_parameters = {
    "REDIS_HOST" : "localhost",
    "REDIS_PORT" : 6379,
    "REDIS_DB" : 0,
    "REDIS_PASSWORD" : "Friends123#"
}

def generate_test_connection() :

    return Redis(
        host = test_config_parameters['REDIS_HOST'],
        port = test_config_parameters['REDIS_PORT'],
        db = test_config_parameters['REDIS_DB'],
        password = test_config_parameters['REDIS_PASSWORD']
    )