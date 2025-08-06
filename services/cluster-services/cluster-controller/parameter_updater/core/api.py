from flask import Flask, request, jsonify
import requests
from .processor import ServiceManager


service_manager = ServiceManager()
app = Flask(__name__)


@app.route('/mgmt', methods=['POST'])
def manage_service():
    try:
        data = request.get_json()

        block_id = data.get("block_id")
        service_type = data.get("service")
        mgmt_action = data.get("mgmt_action")
        mgmt_data = data.get("mgmt_data", {})
        instance_id = data.get("instance_id")

        if block_id == "" and service_type == "stability_checker":
            response = requests.post(
                url="http://localhost:5000",
                json={
                    "mgmt_data": mgmt_data,
                    "mgmt_action": mgmt_action
                }
            )

            return jsonify(response.json())
        
        if block_id != "" and instance_id != "":
            url = f"http://{block_id}-{instance_id}-svc.blocks.svc.cluster.local:18001/mgmt"
            response = requests.post(
                url=url,
                json={
                    "mgmt_data": mgmt_data,
                    "mgmt_action": mgmt_action
                }
            )

            return jsonify(response.json())

        if not service_type or not mgmt_action:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        response = service_manager.execute_mgmt_command(
            block_id, service_type, mgmt_action, mgmt_data)
        return jsonify(response)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def run_server():
    app.run(host='0.0.0.0', port=10000)
