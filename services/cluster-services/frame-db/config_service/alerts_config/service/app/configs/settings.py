import os 

PORT=12000
DEBUG=True
TEST=False
DB_NAME="framedb"

MONGO_URI="mongodb://localhost:27017"

def load_config_at_startup() :
    global PORT 
    global DEBUG
    global TEST
    global MONGO_URI
    global DB_NAME

    PORT = int(os.getenv("PORT", 12000))
    DEBUG = True if os.getenv("MODE", "debug") == "debug" else False
    TEST = True if os.getenv("TEST", "no").lower() == "yes" else False
    MONGO_URI = os.getenv("MONGO_URI", MONGO_URI)
    DB_NAME = os.getenv("DB", DB_NAME)

    print('Loaded config', PORT, DEBUG, TEST, MONGO_URI, DB_NAME)
