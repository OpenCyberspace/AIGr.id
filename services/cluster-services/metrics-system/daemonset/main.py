import os
from core.collectors import MetricsCollector

import logging


def main():

    redis_host = os.getenv("METRICS_REDIS_HOST", "localhost")
    metrics_collector = MetricsCollector(redis_host)

    metrics_collector.run_collector()

    # start metrics server
    metrics_collector.start_server()
    logging.info("started node metrics server")


if __name__ == "__main__":
    main()
