import threading
import queue
import logging
import random
from multiprocessing import Process, Queue, Event, current_process


logging.basicConfig(level=logging.DEBUG)
logging = logging.getLogger(__name__)

class BaseJobExecutor:
    def assign_job(self, job_data, session_id=None):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError


class ThreadJobExecutor(BaseJobExecutor):
    def __init__(self, worker_fn, max_threads=4, max_queue_size=100, sticky_sessions=False):
        self.worker_fn = worker_fn
        self.max_threads = max_threads
        self.sticky_sessions = sticky_sessions

        self.queues = [queue.Queue(maxsize=max_queue_size) for _ in range(max_threads)]
        self.session_to_thread = {}
        self.stop_event = threading.Event()

        for i in range(max_threads):
            t = threading.Thread(target=self._run_worker, args=(i,), daemon=True)
            t.start()
            logging.info(f"[ThreadJobExecutor] Started thread-{i}")

    def _run_worker(self, thread_index):
        while not self.stop_event.is_set():
            try:
                job = self.queues[thread_index].get(timeout=1)
                self.worker_fn(job)
                self.queues[thread_index].task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"[ThreadJobExecutor] Error in thread-{thread_index}: {str(e)}")

    def assign_job(self, job_data, session_id=None):
        try:
            if self.sticky_sessions and session_id:
                thread_index = self.session_to_thread.get(session_id)
                if thread_index is None:
                    thread_index = hash(session_id) % self.max_threads
                    self.session_to_thread[session_id] = thread_index
            else:
                thread_index = random.randint(0, self.max_threads - 1)

            self.queues[thread_index].put_nowait(job_data)
            logging.debug(f"[ThreadJobExecutor] Assigned job to thread-{thread_index}")
            return True
        except queue.Full:
            logging.warning(f"[ThreadJobExecutor] Queue full for thread-{thread_index}")
            return False

    def shutdown(self):
        self.stop_event.set()


class ProcessJobExecutor(BaseJobExecutor):
    def __init__(self, worker_fn, max_threads=4, max_queue_size=100, sticky_sessions=False):
        self.worker_fn = worker_fn
        self.max_threads = max_threads
        self.sticky_sessions = sticky_sessions

        self.queues = [Queue(maxsize=max_queue_size) for _ in range(max_threads)]
        self.session_to_thread = {}
        self.stop_event = Event()
        self.processes = []

        for i in range(max_threads):
            p = Process(target=self._run_worker, args=(i,))
            p.daemon = True
            p.start()
            self.processes.append(p)
            logging.info(f"[ProcessJobExecutor] Started process-{i}")

    def _run_worker(self, index):
        while not self.stop_event.is_set():
            try:
                job = self.queues[index].get(timeout=1)
                self.worker_fn(job)
            except Exception as e:
                continue  # For multiprocessing, can't log easily without sync

    def assign_job(self, job_data, session_id=None):
        try:
            if self.sticky_sessions and session_id:
                idx = self.session_to_thread.get(session_id)
                if idx is None:
                    idx = hash(session_id) % self.max_threads
                    self.session_to_thread[session_id] = idx
            else:
                idx = random.randint(0, self.max_threads - 1)

            self.queues[idx].put_nowait(job_data)
            logging.debug(f"[ProcessJobExecutor] Assigned job from {session_id} to process-{idx}")
            return True
        except queue.Full:
            logging.warning(f"[ProcessJobExecutor] Queue full for process-{idx}")
            return False

    def shutdown(self):
        self.stop_event.set()
        for p in self.processes:
            p.terminate()
