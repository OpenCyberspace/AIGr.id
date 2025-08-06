from flask import Flask, request, jsonify
import logging
from .crud import TemplateStoreDatabase
from .schema import TemplateObject
from .executor import execute_convertor_policy

app = Flask(__name__)
logger = logging.getLogger(__name__)

template_db = TemplateStoreDatabase()


@app.route('/template', methods=['POST'])
def create_template():
    try:
        template_data = request.json
        template = TemplateObject.from_dict(template_data)
        success, result = template_db.insert(template)
        if success:
            return jsonify({"success": True, "data": {"message": "Template created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/template/<string:templateUri>', methods=['GET'])
def get_template(templateUri):
    try:
        success, result = template_db.get_by_templateUri(templateUri)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/template/<string:templateUri>', methods=['PUT'])
def update_template(templateUri):
    try:
        update_data = request.json
        success, result = template_db.update(templateUri, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Template updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/template/<string:templateUri>', methods=['DELETE'])
def delete_template(templateUri):
    try:
        success, result = template_db.delete(templateUri)
        if success:
            return jsonify({"success": True, "data": {"message": "Template deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/templates', methods=['POST'])
def query_templates():
    try:
        query_filter = request.json
        success, results = template_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_templates: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/template/execute', methods=['POST'])
def execute_template_policy():

    try:
        request_data = request.json

        # Extract required fields
        template_uri = request_data.get("template_uri")
        input_data = request_data.get("input_data", {})
        parameters = request_data.get("parameters", {})

        if not template_uri:
            return jsonify({"success": False, "error": "Missing template_uri"}), 400

        # Execute the conversion policy
        converted_data = execute_convertor_policy(
            template_db, input_data, template_uri, parameters)

        return jsonify({"success": True, "data": converted_data}), 200

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 404

    except Exception as e:
        logger.error(f"Error in execute_template_policy: {e}")
        return jsonify({"success": False, "error": "Internal Server Error"}), 500


def run_server():
    app.run(host='0.0.0.0', port=9000)
