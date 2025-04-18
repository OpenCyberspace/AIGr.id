import requests

class NodeManagementAPIs:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
    
    def add_node(self, node_data: dict):
       
        url = f"{self.base_url}/cluster-actions/add-node"
        response = requests.post(url, json=node_data)
        return self._handle_response(response)
    
    def remove_node(self, node_id: str):
        
        url = f"{self.base_url}/cluster-actions/remove-node/{node_id}"
        response = requests.delete(url)
        return self._handle_response(response)
    
    def _handle_response(self, response):
       
        try:
            response_data = response.json()
        except ValueError:
            response.raise_for_status()
        
        if response_data.get("success"):
            return response_data.get("data")
        else:
            raise Exception(response_data.get("message", "Unknown error"))

