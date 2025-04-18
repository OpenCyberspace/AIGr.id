import string
import random
import requests
import os

from .webhooks.component_registry import ComponentRegistry

test_mode = os.getenv("TEST_MODE_ON", "1")

test_data = {
    "componentId": {
        "name": "yolo",
        "version": "v0.0.2",
        "release": "beta"
    },
    "component_uri": "node.algorithm.objdet.yolo:v0.0.02-beta",
    "componentType": "node.algorithm.objdet",
    "containerRegistryInfo": {
        "containerImage": "ubuntu"
    },
    "requiresGPU": True,
    "componentConfig": {
        "requireFrames": True,
        "frameSize": [
            {"width": 416, "height": 416}
        ]
    },
    "componentMetadata": {
        "description": "A testing component used for testing",
        "tags": ["testing", "development", "hello world"],
        "license": "closed",
        "author": {
            "authorName": "prasanna",
            "authorEmail": "prasanan@cognitif.ai",
            "authorLinks": {
                "linkName": "github",
                "url": "https://github.com/Narasimha1997"
            }
        }
    }
}


def generate_unique_alphanumeric_string(N):
    alphanumeric_characters = string.ascii_letters + string.digits
    unique_string = ''.join(random.choices(alphanumeric_characters, k=N))
    return unique_string


def stream_download(url: str, chunk_size: int = 8192) -> bytes:

    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise an exception for HTTP errors

    file_contents = bytearray()

    for chunk in response.iter_content(chunk_size=chunk_size):
        if chunk:  # Filter out keep-alive new chunks
            file_contents.extend(chunk)

    return bytes(file_contents)


def get_component_details(component_uri: str):
    try:

        if test_mode == "1":
            return test_data

        ret, component = ComponentRegistry.GetComponentByURI(component_uri)
        if not ret:
            raise Exception(str(component))

        return component

    except Exception as e:
        raise e
