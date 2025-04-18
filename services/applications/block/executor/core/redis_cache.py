import logging
import redis

logging = logging.getLogger("main")


class RedisConnectionCache:

    def __init__(self):
        self.cache = {}

    def get(self, host: str, port: int):
        cache_key = f"{host}:{port}"

        if cache_key not in self.cache:
            try:
                self.cache[cache_key] = redis.Redis(host=host, port=port)
                logging.info(f"Created new Redis connection: {cache_key}")
            except Exception as e:
                logging.error(
                    f"Failed to connect to Redis at {host}:{port}: {str(e)}")
                return None

        return self.cache[cache_key]
    
    def remove(self, host: str, port: str):
        try:
            cache_key = f"{host}:{port}"
            if cache_key not in self.cache:
                del self.cache[cache_key]
        except Exception as e:
            raise e