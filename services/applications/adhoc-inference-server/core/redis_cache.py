import redis
import logging
import time
from typing import Optional
from .rpc_proxy import InferenceProxyClient

class RedisConnectionCache:
    def __init__(self, max_retries: int = 10, retry_delay: float = 5):
        
        self.cache = {}
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def get(self, host: str, port: int, block_id: Optional[str] = None):
        cache_key = f"{host}:{port}"

        if cache_key not in self.cache:
            try:
                if port == 0:
                    self.cache[cache_key] = InferenceProxyClient(host, block_id)
                    logging.info(f"Created new gRPC connection: {cache_key}")
                else:
                    conn = self._create_redis_connection(host, port, cache_key)
                    if conn:
                        self.cache[cache_key] = conn
            except Exception as e:
                logging.error(f"Initial connection failed for {cache_key}: {str(e)}")
                return None

        if port != 0:
            # Perform a connection health check
            try:
                self.cache[cache_key].ping()
            except redis.exceptions.RedisError as e:
                logging.warning(f"Redis connection lost: {cache_key}, retrying... ({str(e)})")
                self.remove(host, port)
                return self.get(host, port, block_id)

        return self.cache.get(cache_key)

    def _create_redis_connection(self, host: str, port: int, cache_key: str):
        for attempt in range(self.max_retries):
            try:
                conn = redis.Redis(host=host, port=port, socket_connect_timeout=2)
                conn.ping()
                logging.info(f"Created and verified Redis connection: {cache_key}")
                return conn
            except redis.exceptions.RedisError as e:
                logging.warning(f"Retry {attempt+1}/{self.max_retries} failed for {cache_key}: {str(e)}")
                time.sleep(self.retry_delay)

        logging.error(f"All retries failed for Redis connection: {cache_key}")
        return None

    def remove(self, host: str, port: int):
        cache_key = f"{host}:{port}"
        try:
            if cache_key in self.cache:
                del self.cache[cache_key]
                logging.info(f"Removed connection from cache: {cache_key}")
        except Exception as e:
            logging.error(f"Error removing connection {cache_key}: {str(e)}")
            raise e
