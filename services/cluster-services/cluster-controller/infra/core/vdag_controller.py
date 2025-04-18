import requests
import os

class VDAGControllerClient:
    def __init__(self):
        self.base_url = os.getenv("VDAG_CONTROLLER_DB_URL", "http://localhost:10501")

    def _handle_response(self, response):
        """Handle API response: return 'data' on success, raise exception on error."""
        try:
            result = response.json()
        except Exception:
            response.raise_for_status() 

        if result.get("success"):
            return result.get("data")
        else:
            raise Exception(result.get("error", "Unknown error"))

    def create_vdag_controller(self, controller_data):
        url = f"{self.base_url}/vdag-controller"
        response = requests.post(url, json=controller_data)
        return self._handle_response(response)

    def get_vdag_controller(self, controller_id):
        """Retrieve a vDAG Controller by ID."""
        url = f"{self.base_url}/vdag-controller/{controller_id}"
        response = requests.get(url)
        return self._handle_response(response)

    def update_vdag_controller(self, controller_id, update_data):
        """Update an existing vDAG Controller."""
        url = f"{self.base_url}/vdag-controller/{controller_id}"
        response = requests.put(url, json=update_data)
        return self._handle_response(response)

    def delete_vdag_controller(self, controller_id):
        url = f"{self.base_url}/vdag-controller/{controller_id}"
        response = requests.delete(url)
        return self._handle_response(response)

    def query_vdag_controllers(self, query_filter):
        url = f"{self.base_url}/vdag-controllers"
        response = requests.post(url, json=query_filter)
        return self._handle_response(response)

    def list_vdag_controllers_by_vdag_uri(self, vdag_uri):
        url = f"{self.base_url}/vdag-controllers/by-vdag-uri/{vdag_uri}"
        response = requests.get(url)
        return self._handle_response(response)
