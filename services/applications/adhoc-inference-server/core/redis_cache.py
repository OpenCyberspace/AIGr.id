import redis
import logging

from .rpc_proxy import InferenceProxyClient

logging.basicConfig(level=logging.DEBUG)


class RedisConnectionCache:
    def __init__(self):
        self.cache = {}

    def get(self, host: str, port: int):
        cache_key = f"{host}:{port}"

        if cache_key not in self.cache:
            try:
                if port == 0:
                    self.cache[cache_key] = InferenceProxyClient(host)
                    logging.info(f"Created new gRPC connection: {cache_key}")
                else:
                    self.cache[cache_key] = redis.Redis(host=host, port=port)
                    logging.info(f"Created new Redis connection: {cache_key}")
            except Exception as e:
                logging.error(f"Failed to connect to {cache_key}: {str(e)}")
                return None

        return self.cache[cache_key]

    def remove(self, host: str, port: int):
        try:
            cache_key = f"{host}:{port}"
            if cache_key in self.cache:
                del self.cache[cache_key]
        except Exception as e:
            logging.error(f"Error removing connection {cache_key}: {str(e)}")
            raise e
