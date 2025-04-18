import os 

PORT=12000
DEBUG=True
TEST=False
DB_NAME="framedb"

FRAMEBD_CONFIG_URI="mongodb://localhost:27017"
FRAMEDB_MAPPING_URI="mongodb://localhost:27017"
CLUSTER_CONFIG_SVC = None

PUBSUB_HOST = "localhost"
PUBSUB_PORT = 6379
PUBSUB_PASSWORD = None

LOCAL_MODE = False

def load_config_at_startup() :
    global PORT 
    global DEBUG
    global TEST
    global FRAMEBD_CONFIG_URI
    global DB_NAME
    global FRAMEDB_MAPPING_URI
    global LOCAL_MODE

    global PUBSUB_HOST
    global PUBSUB_PORT
    global PUBSUB_PASSWORD

    PORT = int(os.getenv("PORT", 12000))
    DEBUG = True if os.getenv("MODE", "debug") == "debug" else False
    TEST = True if os.getenv("TEST", "no").lower() == "yes" else False


    FRAMEDB_CONFIG_HOST = os.getenv("FRAMEDB_CONFIG_HOST", "localhost:27017")
    FRAMEDB_MAPPING_HOST = os.getenv("FRAMEDB_MAPPING_HOST", "localhost:27017")

    FRAMEBD_MAPPING_USERNAME = os.getenv("FRAMEDB_MAPPING_USER", None)
    FRAMEBD_MAPPING_PASSWORD = os.getenv("FRAMEDB_MAPPING_PASSWORD", None)

    if not FRAMEBD_MAPPING_PASSWORD or not FRAMEBD_MAPPING_USERNAME :
        FRAMEDB_MAPPING_URI = "mongodb://" + FRAMEDB_MAPPING_HOST
    else :
        FRAMEDB_MAPPING_URI = "mongodb://{}:{}@{}".format(
            FRAMEBD_MAPPING_USERNAME, FRAMEBD_MAPPING_PASSWORD, FRAMEDB_MAPPING_HOST
        )
    
    FRAMEDB_CONFIG_USERNAME = os.getenv("FRAMEDB_CONFIG_USER", None)
    FRAMEDB_CONFIG_PASSWORD = os.getenv("FRAMEDB_CONFIG_PASSWORD", None)

    if not FRAMEDB_CONFIG_USERNAME or not FRAMEDB_CONFIG_PASSWORD :
        FRAMEBD_CONFIG_URI = "mongodb://" + FRAMEDB_CONFIG_HOST
    else :
        FRAMEBD_CONFIG_URI = "mongodb://{}:{}@{}".format(
            FRAMEDB_CONFIG_USERNAME, FRAMEDB_CONFIG_PASSWORD, FRAMEDB_CONFIG_HOST
        )

    CLUSTER_CONFIG_SVC = os.getenv("CLUSTER_CONFIG_SVC", None)
    DB_NAME = os.getenv("DB", DB_NAME)

    PUBSUB_HOST = os.getenv("PUBSUB_HOST", "localhost")
    PUBSUB_PORT = int(os.getenv("PUBSUB_PORT", 6379))
    PUBSUB_PASSWORD = os.getenv("PUBSUB_PASSWORD", None)

    LOCAL_MODE = True if os.getenv("LOCAL_MODE", "No").lower() == "yes" else False

    print('Loaded config', PORT, DEBUG, TEST, FRAMEBD_CONFIG_URI, FRAMEDB_MAPPING_URI, DB_NAME)
