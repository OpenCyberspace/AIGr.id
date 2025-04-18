from core.api import run_app

import logging


def main():
    try:
        run_app()
    except Exception as e:
        logging.error(e)

if __name__ == "__main__":
    main()
