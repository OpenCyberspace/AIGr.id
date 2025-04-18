import redis
from queue import Queue
import json
import os


class ReceiverQueue:

    def __init__(self) -> None:
        self.connection = redis.Redis(
            host='localhost', port=6379, password=None,
            db=0
        )

    def get_connection(self):
        return self.connection

    def wait_and_get_data(self, queue_name: str):
        try:

            _, data = self.connection.brpop(queue_name)
            data_json = json.loads(data)

            return True, data_json

        except Exception as e:
            return False, str(e)


class InputInternalQueue:

    def __init__(self, size) -> None:
        self.ip = Queue(size)

    def put(self, data):
        self.ip.put(data)

    def wait_and_get(self):
        return self.ip.get(block=True)


receiver_queue: ReceiverQueue = None
internal_queue: InputInternalQueue = None


def init_internal_queue():
    global internal_queue
    if not internal_queue:
        internal_queue = InputInternalQueue(
            int(os.getenv("INTERNAL_QUEUE_SIZE", 1000))
        )


def init_receiver_queue():
    global receiver_queue
    if not receiver_queue:
        receiver_queue = ReceiverQueue()


def get_internal_queue():
    try:

        if not internal_queue:
            raise Exception("internal_queue is=  not yet initialized")

        return True, internal_queue

    except Exception as e:
        return False, str(e)


def get_receiver_queue():
    try:

        if not receiver_queue:
            raise Exception("receiver_queue is not yet initialized")

        return True, receiver_queue

    except Exception as e:
        return False, str(e)
