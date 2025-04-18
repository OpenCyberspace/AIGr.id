import os 

PORT=12000
DEBUG=True
TEST=False
DB_NAME="framedb"

MONGO_URI="mongodb://localhost:27017"
PERSIST = True

def load_settings() :
    global PORT 
    global DEBUG
    global TEST
    global MONGO_URI
    global DB_NAME
    global PERSIST

    PORT = int(os.getenv("PORT", 12000))
    DEBUG = True if os.getenv("MODE", "debug") == "debug" else False
    TEST = True if os.getenv("TEST", "no").lower() == "yes" else False
    PERSIST = True if os.getenv("PERSIST", "Yes").lower() == "yes" else False

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

    print('Loaded config', PORT, DEBUG, TEST, MONGO_URI, DB_NAME, PERSIST)
