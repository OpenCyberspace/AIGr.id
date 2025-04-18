import logging
import os
import json
import logging
from typing import Dict

from .task_db_status import GlobalTasksDB

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Context:
    def __init__(self):
        try:
            self.task_id: str = os.getenv("TASK_ID", "")
            self.task_status_update_url: str = os.getenv(
                "TASK_STATUS_UPDATE_URL", "")
            self.model_layers_registry_url: str = os.getenv(
                "MODEL_LAYERS_REGISTRY_URL", "")
            self.block_db_url: str = os.getenv("BLOCK_DB_URL", "")

            # Parse TASK_DATA
            task_data_str = os.getenv("TASK_DATA", "{}")
            self.task_data: Dict = json.loads(task_data_str)
            logger.info(
                "Successfully initialized context from environment variables.")
        except json.JSONDecodeError as e:
            logger.exception("Failed to decode TASK_DATA.")
            raise ValueError(f"Invalid JSON in TASK_DATA: {e}")


def execute_model_splitter(container_cls):
    required_methods = ['begin', 'main', 'finish']
    logger.info(
        f"Validating required methods for class '{container_cls.__name__}'.")

    # Validate method presence
    for method in required_methods:
        if not hasattr(container_cls, method) or not callable(getattr(container_cls, method)):
            logger.error(
                f"Missing required method: '{method}' in class '{container_cls.__name__}'.")
            raise AttributeError(
                f"The class '{container_cls.__name__}' must implement a callable method '{method}'.")

    # Initialize context
    try:
        context = Context()
        logger.info("Context initialized successfully.")
    except Exception as e:
        logger.exception("Failed to initialize context.")
        raise RuntimeError(f"Context initialization failed: {e}")

    # Initialize task DB interface
    task_db = GlobalTasksDB()
    task_id = context.task_id

    # Instantiate container class
    try:
        instance = container_cls(context=context)
        logger.info(
            f"Successfully instantiated class '{container_cls.__name__}'.")
    except Exception as e:
        logger.exception("Instantiation failed.")
        task_db.update_task(task_id, "failed", {"error": str(e)})
        raise RuntimeError(
            f"Failed to instantiate class '{container_cls.__name__}': {e}")

    # Run lifecycle methods
    try:
        logger.info("Running begin()...")
        success, result = instance.begin()
        if not success:
            raise RuntimeError(f"begin() failed: {result}")
        extra_data = result

        logger.info("Running main()...")
        success, result = instance.main(extra_data)
        if not success:
            raise RuntimeError(f"main() failed: {result}")
        extra_data = result

        logger.info("Running finish()...")
        success, result = instance.finish(extra_data)
        if not success:
            raise RuntimeError(f"finish() failed: {result}")

        logger.info(
            "All phases completed successfully. Updating task status to 'complete'.")
        task_db.update_task(task_id, "complete", result)
        return result

    except Exception as e:
        logger.exception("Error during execution.")
        task_db.update_task(task_id, "failed", {"error": str(e)})
        raise
