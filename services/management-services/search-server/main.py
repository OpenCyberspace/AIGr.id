from flask import Flask, request, jsonify
import logging

from core.action import filter_data, similarity_search
from core.similarity_search import SimilaritySearch, FilterSearch

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


@app.route('/api/filter-data', methods=['POST'])
def api_filter_data():
    try:
        input_data = request.get_json()
        if not input_data:
            raise ValueError("Missing or invalid JSON body")

        result = filter_data(input_data)

        logging.info(f"filter search output: {result}")

        # Success response
        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        logging.error(f"Error in /api/filter-data: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/similarity-search', methods=['POST'])
def api_similarity_search():
    try:
        input_data = request.get_json()
        if not input_data:
            raise ValueError("Missing or invalid JSON body")

        result = similarity_search(input_data)

        logging.info(f"similarity search output: {result}")

        # Success response
        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        logging.error(f"Error in /api/similarity-search: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/no-ir/similarity-search', methods=['POST'])
def api_similarity_search_no_ir():
    try:
        input_data = request.get_json()
        if not input_data:
            raise ValueError("Missing or invalid JSON body")

        search = SimilaritySearch(input_data)
        result = search.execute()

        logging.info(f"similarity search output: {result}")

        # Success response
        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        logging.error(f"Error in /api/similarity-search: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/api/no-ir/filter', methods=['POST'])
def api_filter_search_no_ir():
    try:
        input_data = request.get_json()
        if not input_data:
            raise ValueError("Missing or invalid JSON body")

        search = FilterSearch(input_data)
        result = search.execute()

        logging.info(f"filter search output: {result}")

        # Success response
        return jsonify({"success": True, "data": result}), 200

    except Exception as e:
        logging.error(f"Error in /api/similarity-search: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12000, debug=True)
