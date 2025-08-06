import os
import json

class Env:

    def __init__(self) -> None:
        self.vdag_uri = os.getenv("VDAG_URI")
        self.vdag_db_server_uri = os.getenv("VDAG_DB_API_URL", "http://localhost:10501")
        self.adhoc_inference_server_uri = os.getenv("VDAG_ADHOC_INFERENCE_SERVER_URL", "http://localhost:50052")
        self.stream_redis_db_uri = os.getenv("STREAMING_REDIS_DB_URL", "localhost")
        init_data = os.getenv("VDAG_CUSTOM_INIT_DATA", None)

        self.vdag_custom_init_data = {}
        if init_data:
            self.vdag_custom_init_data = json.loads(init_data)
    