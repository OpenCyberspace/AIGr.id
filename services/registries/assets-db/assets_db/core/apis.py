from flask import Flask, request, jsonify, send_file
from .db import AssetStoreDatabase
from .schema import AssetObject
from .fs import Storage

from uuid import uuid4

import json
import os
from io import BytesIO


import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)
asset_db = AssetStoreDatabase()


@app.route('/asset', methods=['POST'])
def create_asset():
    try:
        asset_data = request.json
        asset = AssetObject.from_dict(asset_data)
        success, result = asset_db.insert(asset)
        if success:
            return jsonify({"success": True, "data": {"message": "Asset created", "id": str(result)}}), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_asset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/asset/<string:asset_uri>', methods=['GET'])
def get_asset(asset_uri):
    try:
        success, result = asset_db.get_by_asset_uri(asset_uri)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_asset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/asset/<string:asset_uri>', methods=['PUT'])
def update_asset(asset_uri):
    try:
        update_data = request.json
        success, result = asset_db.update(asset_uri, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Asset updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_asset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/asset/<string:asset_uri>', methods=['DELETE'])
def delete_asset(asset_uri):
    try:
        success, result = asset_db.delete(asset_uri)
        if success:
            return jsonify({"success": True, "data": {"message": "Asset deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_asset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/assets', methods=['POST'])
def query_assets():
    try:
        query_filter = request.json
        success, results = asset_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_assets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/upload_asset", methods=["POST"])
def upload_asset():
    try:
        # Validate file input
        if "asset" not in request.files:
            return jsonify({"success": False, "message": "No file part"}), 400

        file = request.files["asset"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No selected file"}), 400

        # Get metadata from form
        asset_metadata = request.form.get("asset_metadata", "{}")
        metadata_dict = json.loads(asset_metadata)

        # Ensure required fields exist
        asset_name = metadata_dict.get("asset_name", "").strip()
        asset_version = metadata_dict.get("asset_version", {})
        version = asset_version.get("version", "").strip()
        tag = asset_version.get("tag", "").strip()

        if not asset_name:
            return jsonify({"success": False, "message": "asset_name is required"}), 400
        if not version or not tag:
            return jsonify({"success": False, "message": "Both version and tag are required in asset_version"}), 400

        # Generate a secure filename
        asset_id = str(uuid4())

        public_url = Storage().upload_file(file, asset_id, content_type=file.content_type)
        if not public_url:
            return jsonify({"success": False, "message": "File upload failed"}), 500

        file.seek(0, os.SEEK_END)

        asset_tags = metadata_dict.get("asset_tags", [])
        asset_metadata = metadata_dict.get("asset_metadata", {})

        asset_file_info = metadata_dict.get('asset_file_info', {})
        asset_file_info.update({
            "file_type": file.content_type,
            "file_size": file.content_length
        })

        # Create asset dictionary for AssetObject
        asset_data = {
            "asset_name": asset_name,
            "asset_version": {"version": version, "tag": tag},
            "asset_metadata": asset_metadata,
            "asset_public_url": public_url,
            "asset_file_info": asset_file_info,
            "asset_tags": asset_tags,
            "asset_id": asset_id
        }

        asset_object = AssetObject.from_dict(asset_data)

        success, message = asset_db.insert(asset_object)
        if not success:
            return jsonify({"success": False, "message": message}), 500

        return jsonify({"success": True, "asset_uri": asset_object.asset_uri, "asset_id": asset_id, "public_url": public_url}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/asset-object/<asset_id>", methods=["GET"])
def get_asset_object(asset_id):
    try:
        file_obj = Storage().download_file(asset_id)
        if not file_obj:
            return jsonify({"success": False, "message": "File not found"}), 404

        file_data = BytesIO(file_obj.read())

        return send_file(
            file_data,
            mimetype=file_obj.content_type,
            as_attachment=True,
            download_name=asset_id
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"success": True, "message": "healthy"}), 200

def run_server():
    app.run(host='0.0.0.0', port=4000)
