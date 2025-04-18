import os 

if os.getenv("LOGGING", "No").lower() == "yes" :
    import config
else :
    import logging
    logging.basicConfig(level = logging.INFO)

from app import app
