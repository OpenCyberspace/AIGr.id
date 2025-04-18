from flask import Flask, request, jsonify
from .blocks import Blocks
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

blocks = Blocks()
blocks.load_health_checkers_from_redis()


@app.route('/register', methods=['POST'])
def register_health_checker():
    try:
        data = request.json
        if 'id' not in data or 'data' not in data:
            return jsonify({"success": False, "error": "Invalid input data"}), 400

        checker_id = data['id']
        checker_data = data['data']
        blocks.register_health_checker(checker_id, checker_data)
        return jsonify({"success": True, "message": "Health checker registered successfully"}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/unregister/<string:checker_id>', methods=['DELETE'])
def unregister_health_checker(checker_id):
    try:
        blocks.unregister_health_checker(checker_id)
        return jsonify({"success": True, "message": "Health checker unregistered successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health_checkers', methods=['GET'])
def get_health_checkers():
    try:
        health_checkers = blocks.load_health_checkers_from_redis()
        return jsonify({"success": True, "data": health_checkers}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/mgmt', methods=['POST'])
def mgmt():
    try:

        data = request.json

        response = blocks.mgmt(
            data['block_id'],
            data['action'],
            data['data']
        )

        return jsonify({"success": True, "data": response}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


def run_app():
    logging.info(
        "starting HTTP server at port 7000, listening for block registrations")
    app.run(host='0.0.0.0', port=5555)
