import os 

PORT=12000
DEBUG=True
TEST=False
DB_NAME="framedb"
FRAMEDB_PASSWORD = None

MONGO_URI="mongodb://localhost:27017"
ROUTING_REASSIGN_API = "http://localhost:8000/routing/reassignInstance"

def load_config_at_startup() :
    global PORT 
    global DEBUG
    global TEST
    global MONGO_URI
    global DB_NAME
    global ROUTING_REASSIGN_API
    global FRAMEDB_PASSWORD

    PORT = int(os.getenv("PORT", 12000))
    DEBUG = True if os.getenv("MODE", "debug") == "debug" else False
    TEST = True if os.getenv("TEST", "no").lower() == "yes" else False

    MONGO_HOST = os.getenv("FRAMEDB_HOST", "localhost:27017")

    MONGO_USERNAME = os.getenv("FRAMEDB_USER", None)
    MONO_PASSWORD = os.getenv("FRAMEDB_PASSWORD", None)

    if not MONGO_USERNAME or not MONO_PASSWORD :
        MONGO_URI = "mongodb://{}".format(MONGO_HOST)
    else :
        MONGO_URI = "mongodb://{}:{}@{}".format(
            MONGO_USERNAME, MONO_PASSWORD, MONGO_HOST
        )
    
    DB_NAME = os.getenv("DB", DB_NAME)
    ROUTING_REASSIGN_API = os.getenv("ROUTING_REASSIGN_API", "http://localhost:8000/routing/reassignInstance")
    FRAMEDB_PASSWORD = os.getenv("DEPLOYMENT_PASSWORD", None)


    print('Loaded config', PORT, DEBUG, TEST, MONGO_URI, DB_NAME, ROUTING_REASSIGN_API)
