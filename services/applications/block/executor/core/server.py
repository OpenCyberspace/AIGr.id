import os
import time
import threading
import logging


from .aios_packet_pb2 import AIOSPacket
from .globals import get_receiver_queue, get_internal_queue
from .redis_cache import RedisConnectionCache
from .metrics import AIOSMetrics


logging.basicConfig(level=logging.INFO)


class RedisListener:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.queue_name = "EXECUTOR_INPUTS"
        self.executor_host = os.getenv("EXECUTOR_REDIS_HOST", "localhost")
        self.redis_cache = RedisConnectionCache()
        self.redis_client = self.redis_cache.get(
            self.redis_host, self.redis_port)
        self.metrics = AIOSMetrics(os.getenv("BLOCK_ID"))

        self.metrics.register_counter(
            "tasks_processed", "number of tasks processed by the inference server")
        self.metrics.register_gauge(
            "latency", "average end to end latency of tasks")
        self.metrics.start_http_server()

    def listen(self):
        logging.info("Listening for jobs on Redis queue: %s", self.queue_name)
        while True:
            try:
                _, job_data = self.redis_client.brpop(self.queue_name)

                st = time.time()

                packet = AIOSPacket()
                packet.ParseFromString(job_data)

                ret, internal_queue = get_internal_queue()
                if not ret:
                    raise Exception("Failed to get internal queue")

                internal_queue.put({
                    "packet": packet,
                    "raw": job_data
                })
    
                et = time.time()

                self.metrics.set_gauge("latency", et - st)
                self.metrics.increment_counter("tasks_processed")

            except Exception as e:
                logging.error("Error processing job: %s", e)
                self.redis_cache.remove(self.redis_host, self.redis_port)
                self.redis_client = self.redis_cache.get(
                    self.redis_host, self.redis_port)



def serve():
    redis_listener = RedisListener()
    redis_listener.listen()


def serve_in_thread():
    server_thread = threading.Thread(target=serve)
    server_thread.start()
    return server_thread
