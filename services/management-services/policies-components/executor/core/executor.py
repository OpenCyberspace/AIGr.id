from multiprocessing import Process, Queue, Semaphore
import os
from .db import PolicyDB
from .code_executor import LocalCodeExecutor
import logging
from multiprocessing import Process, Queue, Semaphore
import os
import logging
from typing import Dict, Any


class PolicyFunctionExecutor:
    def __init__(self):
        self.policy_db = PolicyDB()

    def execute(self, policy_rule_uri: str, parameters: dict = None, input_data: dict = None):

        if not input_data:
            raise ValueError("input_data is mandatory and cannot be None.")

        logging.info(f"Fetching policy data for URI: {policy_rule_uri}")
        policy_data = self.policy_db.read(policy_rule_uri)
        if not policy_data:
            raise ValueError(
                f"Policy rule with URI '{policy_rule_uri}' not found.")

        logging.info("Determining parameters for execution")
        policy_parameters = policy_data.policy_parameters
        if parameters is None:
            parameters = policy_parameters

        logging.info(
            f"Initializing LocalCodeExecutor for policy {policy_rule_uri}")
        try:
            executor = LocalCodeExecutor(
                download_url=policy_data.code,
                settings=policy_data.policy_settings,
                parameters=parameters,
            )
            results = executor.execute(input_data)
            logging.info(
                f"Execution completed successfully for policy {policy_rule_uri}")
            return results
        except Exception as e:
            logging.error(
                f"Failed to execute policy function for URI '{policy_rule_uri}': {e}")
            raise


logging.basicConfig(level=logging.INFO)


class MultiprocessingPolicyRuleExecutor:
    def __init__(self):

        max_processes = int(os.getenv("MAX_PROCESSES", "0"))
        self.semaphore = Semaphore(
            max_processes) if max_processes > 0 else None
        self.processes = {}  # Track running processes

    def _execute_in_process(self, policy_rule_uri, parameters, input_data, result_queue):

        try:
            executor = PolicyFunctionExecutor()
            result = executor.execute(policy_rule_uri, parameters, input_data)
            result_queue.put(result)
        except Exception as e:
            logging.error(f"Error in subprocess execution: {e}")
            result_queue.put({"success": False, "message": str(e)})
        finally:
            if self.semaphore:
                self.semaphore.release()

    def execute(self, policy_rule_uri: str, parameters: Dict[str, Any] = None, input_data: Dict[str, Any] = None) -> Queue:

        if not input_data:
            raise ValueError("input_data is mandatory and cannot be None.")

        if self.semaphore:
            self.semaphore.acquire()

        result_queue = Queue()

        process = Process(
            target=self._execute_in_process,
            args=(policy_rule_uri, parameters, input_data, result_queue)
        )
        process.start()

        self.processes[process.pid] = (process, result_queue)

        logging.info(
            f"Started process {process.pid} for policy {policy_rule_uri}")
        return result_queue
