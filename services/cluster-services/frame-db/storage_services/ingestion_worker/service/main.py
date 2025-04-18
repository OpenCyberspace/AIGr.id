import os 

if os.getenv("LOGGING", "No").lower() == "yes" :
    import config
else :
    import logging
    logging.basicConfig(level = logging.INFO)

from worker import start_task

if __name__ == "__main__":
    start_task()
