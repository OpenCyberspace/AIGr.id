
import os
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError


class Storage:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            region_name=os.getenv("AWS_REGION")
        )
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        self.public_url = os.getenv("PUBLIC_URL")

    def upload_file(self, file_stream, asset_id, content_type=None):
        try:
            s3_key = f"asset/{asset_id}"
            extra_args = {"ContentType": content_type} if content_type else {}

            self.s3_client.upload_fileobj(
                file_stream, self.bucket_name, s3_key, ExtraArgs=extra_args)

            return f"{self.public_url}/asset-object/{asset_id}"
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None

    def download_file(self, asset_id):
        try:
            s3_key = f"asset/{asset_id}"
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=s3_key)
            return response["Body"]
        except Exception as e:
            print(f"Error downloading file: {e}")
            return None
