from core.server import run_app
import logging
import time


def main():
    try:
        run_app()
    except Exception as e:
        logging.error(
            f"error_failure_notifier_service: {e}, restarting in 10s")


if __name__ == "__main__":
    main()
