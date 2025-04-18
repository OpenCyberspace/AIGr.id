import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError, PartialCredentialsError, ClientError
from io import BytesIO

import pickle
import os
import redis
from collections.abc import MutableMapping


class S3UploadError(Exception):
    pass


class S3DownloadError(Exception):
    pass


class AssetsRegistry:
    def __init__(self, bucket_name, aws_access_key_id=None, aws_secret_access_key=None, aws_region=None):
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

    def upload_file_by_path(self, object_id, file_path):
        try:
            self.s3.upload_file(file_path, self.bucket_name, object_id)
        except (BotoCoreError, ClientError) as e:
            raise S3UploadError(
                f"Failed to upload file {file_path} to S3: {str(e)}")

    def upload_file_by_bytes(self, object_id, file_bytes):
        try:
            self.s3.put_object(Bucket=self.bucket_name,
                               Key=object_id, Body=file_bytes)
        except (BotoCoreError, ClientError) as e:
            raise S3UploadError(
                f"Failed to upload bytes data to S3 with object ID {object_id}: {str(e)}")

    def upload_file_by_buffer(self, object_id, file_buffer):
        try:
            file_buffer.seek(0)
            self.s3.put_object(Bucket=self.bucket_name,
                               Key=object_id, Body=file_buffer)
        except (BotoCoreError, ClientError) as e:
            raise S3UploadError(
                f"Failed to upload buffer to S3 with object ID {object_id}: {str(e)}")

    def download_file_to_path(self, object_id, file_path):
        try:
            self.s3.download_file(self.bucket_name, object_id, file_path)
        except (BotoCoreError, ClientError) as e:
            raise S3DownloadError(
                f"Failed to download file with object ID {object_id} to path {file_path}: {str(e)}")

    def download_file_as_bytes(self, object_id):
        try:
            response = self.s3.get_object(
                Bucket=self.bucket_name, Key=object_id)
            return response['Body'].read()
        except (BotoCoreError, ClientError) as e:
            raise S3DownloadError(
                f"Failed to download bytes data for object ID {object_id}: {str(e)}")

    def download_file_as_buffer(self, object_id):
        try:
            response = self.s3.get_object(
                Bucket=self.bucket_name, Key=object_id)
            file_buffer = BytesIO(response['Body'].read())
            file_buffer.seek(0)
            return file_buffer
        except (BotoCoreError, ClientError) as e:
            raise S3DownloadError(
                f"Failed to download buffer for object ID {object_id}: {str(e)}")


class StateDict(MutableMapping):
    def __init__(self, namespace):
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))
        redis_password = os.getenv('REDIS_PASSWORD', None)

        self.namespace = namespace
        self.redis_client = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )

    def _prefixed_key(self, key):
        return f"{self.namespace}:{key}"

    def __getitem__(self, key):
        value = self.redis_client.get(self._prefixed_key(key))
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        self.redis_client.set(self._prefixed_key(key), value)

    def __delitem__(self, key):
        if not self.redis_client.delete(self._prefixed_key(key)):
            raise KeyError(key)

    def __iter__(self):
        namespace_prefix = f"{self.namespace}:*"
        for key in self.redis_client.scan_iter(match=namespace_prefix):
            yield key[len(self.namespace) + 1:]

    def __len__(self):
        namespace_prefix = f"{self.namespace}:*"
        return len(list(self.redis_client.scan_iter(match=namespace_prefix)))

    def __contains__(self, key):
        return self.redis_client.exists(self._prefixed_key(key))

    def clear(self):
        namespace_prefix = f"{self.namespace}:*"
        keys = list(self.redis_client.scan_iter(match=namespace_prefix))
        if keys:
            self.redis_client.delete(*keys)

    def keys(self):
        namespace_prefix = f"{self.namespace}:*"
        return [key[len(self.namespace) + 1:] for key in self.redis_client.scan_iter(match=namespace_prefix)]

    def values(self):
        return (self.redis_client.get(self._prefixed_key(key)) for key in self.keys())

    def items(self):
        return ((key, self.redis_client.get(self._prefixed_key(key))) for key in self.keys())

    def get(self, key, default=None):
        value = self.redis_client.get(self._prefixed_key(key))
        return value if value is not None else default

    def pop(self, key, default=None):
        try:
            value = self.__getitem__(key)
            self.__delitem__(key)
            return value
        except KeyError:
            if default is not None:
                return default
            raise

    def popitem(self):
        for key in self.keys():
            value = self.__getitem__(key)
            self.__delitem__(key)
            return key, value
        raise KeyError("popitem(): dictionary is empty")

    def update(self, *args, **kwargs):
        if args:
            other = dict(args[0])
            for key, value in other.items():
                self.__setitem__(key, value)
        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def setdefault(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            self.__setitem__(key, default)
            return default

    def __repr__(self):
        return f"{self.__class__.__name__}({dict(self.items())})"


class StateDictV2(MutableMapping):
    BASIC_TYPES = (str, int, float, bool, type(None))

    def __init__(self, namespace):
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))
        redis_password = os.getenv('REDIS_PASSWORD', None)

        self.namespace = namespace
        self.redis_client = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )

    def _prefixed_key(self, key):
        return f"{self.namespace}:{key}"

    def _type_key(self, key):
        return f"{self.namespace}:type:{key}"

    def __getitem__(self, key):
        type_key = self._type_key(key)
        data_type = self.redis_client.get(type_key)

        if data_type is None:
            raise KeyError(key)

        value = self.redis_client.get(self._prefixed_key(key))

        if data_type == 'basic':
            return value
        elif data_type == 'pickle':
            return pickle.loads(self.redis_client.get(self._prefixed_key(key)))
        else:
            raise ValueError(f"Unknown data type for key {key}: {data_type}")

    def __setitem__(self, key, value):
        type_key = self._type_key(key)

        if isinstance(value, self.BASIC_TYPES):
            self.redis_client.set(self._prefixed_key(key), value)
            self.redis_client.set(type_key, 'basic')
        else:
            self.redis_client.set(self._prefixed_key(key), pickle.dumps(value))
            self.redis_client.set(type_key, 'pickle')

    def __delitem__(self, key):
        if not self.redis_client.delete(self._prefixed_key(key)):
            raise KeyError(key)
        self.redis_client.delete(self._type_key(key))

    def __iter__(self):
        namespace_prefix = f"{self.namespace}:*"
        type_prefix = f"{self.namespace}:type:*"

        keys = set(self.redis_client.scan_iter(match=namespace_prefix)
                   ) - set(self.redis_client.scan_iter(match=type_prefix))

        for key in keys:
            yield key[len(self.namespace) + 1:]

    def __len__(self):
        namespace_prefix = f"{self.namespace}:*"
        type_prefix = f"{self.namespace}:type:*"

        keys = set(self.redis_client.scan_iter(match=namespace_prefix)
                   ) - set(self.redis_client.scan_iter(match=type_prefix))

        return len(keys)

    def __contains__(self, key):
        return self.redis_client.exists(self._prefixed_key(key))

    def clear(self):
        namespace_prefix = f"{self.namespace}:*"
        type_prefix = f"{self.namespace}:type:*"

        keys = list(self.redis_client.scan_iter(match=namespace_prefix))
        type_keys = list(self.redis_client.scan_iter(match=type_prefix))

        if keys:
            self.redis_client.delete(*keys)
        if type_keys:
            self.redis_client.delete(*type_keys)

    def keys(self):
        namespace_prefix = f"{self.namespace}:*"
        type_prefix = f"{self.namespace}:type:*"

        keys = set(self.redis_client.scan_iter(match=namespace_prefix)
                   ) - set(self.redis_client.scan_iter(match=type_prefix))

        return [key[len(self.namespace) + 1:] for key in keys]

    def values(self):
        for key in self.keys():
            yield self.__getitem__(key)

    def items(self):
        for key in self.keys():
            yield key, self.__getitem__(key)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def pop(self, key, default=None):
        try:
            value = self.__getitem__(key)
            self.__delitem__(key)
            return value
        except KeyError:
            if default is not None:
                return default
            raise

    def popitem(self):
        for key in self.keys():
            value = self.__getitem__(key)
            self.__delitem__(key)
            return key, value
        raise KeyError("popitem(): dictionary is empty")

    def update(self, *args, **kwargs):
        if args:
            other = dict(args[0])
            for key, value in other.items():
                self.__setitem__(key, value)
        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def setdefault(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            self.__setitem__(key, default)
            return default

    def __repr__(self):
        return f"{self.__class__.__name__}({dict(self.items())})"


class Session:

    def __init__(self, session_id, session_init_data) -> None:
        self.session_id = session_id
        self.session_data = session_init_data

    def get_id(self):
        return self.session_id

    def get_data(self):
        return self.session_data


class SessionsManager:

    def __init__(self) -> None:
        self.sessions_data = {}

    def create_session(self, session_id, init_data):
        self.sessions_data[session_id] = Session(
            session_id, init_data
        )

    def get_session_object(self, session_id):
        try:
            session_object = self.sessions_data.get(session_id)
            if not session_object:
                raise Exception("session {} not found", session_id)
            return True, session_object
        except Exception as e:
            return False, str(e)

    def update_session_object(self, session_id, data):
        try:
            self.sessions_data[session_id].session_data = data
            return True, "session data updated"
        except Exception as e:
            return False, str(e)

    def get_session_data(self, session_id):
        try:
            session_object = self.sessions_data.get(session_id)
            if not session_object:
                raise Exception("session {} not found".format(session_id))
            return True, session_object.get_data()
        except Exception as e:
            return False, str(e)

    def remove_sessions_data(self, session_id):
        try:

            if not session_id in self.sessions_data:
                raise Exception("session {} not found".format(session_id))

            del self.sessions_data[session_id]

        except Exception as e:
            return False, str(e)

    def get_dict_ref(self):
        return self.sessions_data

    def clear(self):
        self.sessions_data.clear()



