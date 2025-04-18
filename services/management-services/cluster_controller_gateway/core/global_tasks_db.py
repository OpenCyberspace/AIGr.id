import os
import requests
import logging

class GlobalTasksDB:
    def __init__(self):
        self.base_url = os.getenv("GLOBAL_TASKS_DB_URL", "http://localhost:8000")
        self.session = requests.Session()

    def create_task(self, task_type: str, task_data: dict, task_status: str = "pending") -> str:
        """Creates a new task and returns the task ID."""
        url = f"{self.base_url}/task"
        payload = {
            "task_type": task_type,
            "task_data": task_data,
            "task_status": task_status,
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data["data"].get("task_id")
            else:
                logging.error("Task creation failed: %s", data)
                raise ValueError("Failed to create task")
        except requests.RequestException as e:
            logging.exception("Error while creating task")
            raise
    
    def update_task(self, task_id: str, status: str, task_status_data: dict):
        """Updates the task status."""
        url = f"{self.base_url}/task_update"
        payload = {
            "task_id": task_id,
            "status": status,
            "task_status_data": task_status_data,
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.exception("Error while updating task")
            raise