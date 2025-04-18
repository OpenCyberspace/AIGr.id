import logging
import time
from typing import Dict
import redis
from google.protobuf.message import Message

logger = logging.getLogger(__name__)


class BlockSideCars:
    def __init__(self, block_id: str, sidecars: Dict[str, Dict]):
        self.block_id = block_id
        self.sidecars_config = sidecars
        self.redis_clients = {}  # name -> redis.Redis
        self.redis_url_template = "{name}-{block_id}-svc.sidecars.svc.cluster.local"
        self.port = 6379

    def _get_redis_url(self, name: str, config: Dict) -> str:
        if config.get("external", False):
            return config.get("external_redis_url")
        return f"{name}-{self.block_id}-svc.sidecars.svc.cluster.local"

    def _connect(self, name: str) -> redis.Redis:
        config = self.sidecars_config.get(name)
        if not config:
            raise ValueError(f"No config found for sidecar: {name}")

        url = self._get_redis_url(name, config)
        logger.debug(f"Connecting to Redis for sidecar {name} at {url}:{self.port}")

        client = redis.Redis(host=url, port=self.port, socket_connect_timeout=5)
        self.redis_clients[name] = client
        return client

    def _get_or_connect(self, name: str) -> redis.Redis:
        return self.redis_clients.get(name) or self._connect(name)

    def push_to_sidecar(self, name: str, input_proto: Message):
        if name not in self.sidecars_config:
            raise ValueError(f"Unknown sidecar: {name}")

        serialized = input_proto.SerializeToString()
        client = self._get_or_connect(name)

        for attempt in range(2):  # try original, then one reconnect attempt
            try:
                client.rpush("INPUTS", serialized)
                logger.debug(f"Pushed input to sidecar '{name}'")
                return
            except redis.exceptions.RedisError as e:
                logger.warning(f"Push failed to sidecar '{name}', attempt {attempt + 1}: {e}")
                if attempt == 0:
                    client = self._connect(name)
                else:
                    logger.error(f"Final push attempt to sidecar '{name}' failed.")
                    raise

    def push_to_all_sidecars(self, input_proto: Message):
        for name in self.sidecars_config:
            try:
                self.push_to_sidecar(name, input_proto)
            except Exception as e:
                logger.error(f"Failed to push to sidecar '{name}': {e}")
