from core.app import run_server_thread
from core.processor import start_listeners

if __name__ == "__main__":
    start_listeners(run_server_thread)
