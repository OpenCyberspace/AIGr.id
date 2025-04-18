import time
import os
import logging
import threading

from .scanner import NamespaceScanner
from .controller_actions import ClusterControllerExecutor
from .nodes_server import run_server


class ScannerIterator:
    def __init__(self, namespace: str, interval: int, controller_base_url: str):
        self.namespace_scanner = NamespaceScanner(namespace)
        self.interval = interval
        self.controller_executor = ClusterControllerExecutor(
            controller_base_url)
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def run(self):
        while True:
            failed_pods = self.namespace_scanner.get_failed_pods()
            if failed_pods:
                payload = {"failed_pods": failed_pods}
                self.logger.info(f"Sending failed pods data: {payload}")
                self.controller_executor.failed_instances(payload)
            else:
                self.logger.info("No failed pods detected.")

            time.sleep(self.interval)


def initialize_checker():
    interval = int(os.getenv("PODS_CHECK_INTERVAL", "60"))
    namespace = os.getenv("BLOCKS_NAMESPACE", "blocks")

    scanner = ScannerIterator(namespace=namespace, interval=interval, controller_base_url="http://localhost:4000")
    return scanner


class InfraChecker:

    def __init__(self) -> None:
        self.init_checker = initialize_checker()

    def start_checker(self):
        self.init_checker.run()

    def start_server(self):
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()


def run_system():
    try:
        init_checker = InfraChecker()
        init_checker.start_server()

        init_checker.start_checker()

    except Exception as e:
        logging.error(f"error: {e}")
