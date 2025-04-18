import redis
import logging
import json


class ParserEventListener:
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0, queue_name='PARSER_EVENTS'):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.queue_name = queue_name
        self.redis_client = redis.StrictRedis(
            host=self.redis_host, port=self.redis_port, db=self.redis_db)

        # Configure logging
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def listen(self):
        self.logger.info(f"Listening on Redis queue: {self.queue_name}")
        while True:
            _, message = self.redis_client.brpop(self.queue_name)
            self.handle_event(message)

    def handle_event(self, message):
        return json.loads(message)
