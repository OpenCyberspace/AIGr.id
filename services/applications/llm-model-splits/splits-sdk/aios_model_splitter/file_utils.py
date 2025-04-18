import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError
import os
import hashlib
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3Manager:
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name='us-east-1'):
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
            logger.info("Initialized S3 client successfully.")
        except Exception as e:
            logger.exception("Failed to initialize S3 client.")
            raise

    def upload_file(self, file_path, bucket_name, object_key):
        try:
            self.s3_client.upload_file(file_path, bucket_name, object_key)
            logger.info(f"File uploaded to s3://{bucket_name}/{object_key}")
            return True
        except (BotoCoreError, ClientError) as e:
            logger.exception("Failed to upload file to S3.")
            return False

    def download_file(self, bucket_name, object_key, destination_path):
        try:
            self.s3_client.download_file(bucket_name, object_key, destination_path)
            logger.info(f"File downloaded from s3://{bucket_name}/{object_key} to {destination_path}")
            return True
        except (BotoCoreError, ClientError) as e:
            logger.exception("Failed to download file from S3.")
            return False


class FileDownloader:
    def download(self, url, target_path):
        try:
            logger.info(f"Starting download from {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=4194304):
                    f.write(chunk)

            logger.info(f"File downloaded successfully to {target_path}")
            return True
        except requests.exceptions.RequestException as e:
            logger.exception(f"Download failed from {url}")
            return False
        except OSError as e:
            logger.exception(f"Failed to write file to {target_path}")
            return False


class LayerHash:
    def get_hash(self, file_path):
        
        if not os.path.isfile(file_path):
            logger.error(f"File does not exist: {file_path}")
            return None

        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            md5_hash = hash_md5.hexdigest()
            logger.info(f"Computed MD5 hash for {file_path}: {md5_hash}")
            return md5_hash
        except Exception as e:
            logger.exception(f"Error while computing hash for {file_path}")
            return None

