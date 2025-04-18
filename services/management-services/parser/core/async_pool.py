import threading
from concurrent.futures import ThreadPoolExecutor
import queue


class ThreadPoolQueueSystem:
    def __init__(self, max_workers=5):
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()

    def submit_task(self, func, *args, **kwargs):
        self.task_queue.put((func, args, kwargs))
        self._schedule_task()

    def _schedule_task(self):
        while not self.task_queue.empty():
            func, args, kwargs = self.task_queue.get()
            self.executor.submit(self._process_task, func, *args, **kwargs)

    def _process_task(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            with self.lock:
                self.result_queue.put(result)
        except Exception as e:
            self.result_queue.put(e)

    def wait_for_result(self, timeout=None):
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(
                "No result available within the timeout period.")

    def shutdown(self):
        self.executor.shutdown(wait=True)
