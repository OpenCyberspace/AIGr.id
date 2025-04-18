from .env import get_env_settings
#load env settings at start-time
get_env_settings()

from .task import Task

def start_task():
    worker = Task()
    worker.run_task()