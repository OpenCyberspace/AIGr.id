import grpc
import time
import logging
from pathlib import Path
from uuid import uuid4
import json
from concurrent.futures import ThreadPoolExecutor

from core.vdag_service_pb2 import vDAGInferencePacket, vDAGFileInfo
from core.vdag_service_pb2_grpc import vDAGInferenceServiceStub

# Configure logging
logging.basicConfig(level=logging.INFO)


def load_file_info(file_path: str, metadata: str = "") -> vDAGFileInfo:
    with open(file_path, "rb") as f:
        file_data = f.read()
    return vDAGFileInfo(metadata=metadata, file_data=file_data)


def send_inference_request(seq_no: int):
    channel = grpc.insecure_channel("35.232.150.117:32121")
    stub = vDAGInferenceServiceStub(channel)

    data = {
        "mode": "chat",
        "gen_params": {
            "temperature": 0.1,
            # "min_p": 0.01,
            # "top_k": 64,
            "top_p": 0.95,
            "max_tokens": 4096  # Set a limit for the response length
        },
        "messages": [{"content": [
            {"type": "text", "text": "Analyze the following image and generate your objective scene report.?"},
            {"type": "image_url",
             "image_url": {"url": "https://akm-img-a-in.tosshub.com/indiatoday/images/story/202311/chain-snatching-caught-on-camera-in-bengaluru-293151697-16x9_0.jpg"}}]}]
    }
    ts = time.time()

    # Optional file
    example_file = Path("example.txt")
    if example_file.exists():
        files = [load_file_info(str(example_file), metadata=f"seq_{seq_no}")]
    else:
        files = []

    session_id = str(uuid4())

    request = vDAGInferencePacket(
        session_id=session_id,
        seq_no=seq_no,
        frame_ptr=b"",
        data=json.dumps(data),
        ts=ts,
        files=files
    )

    try:
        logging.info(f"[seq_no={seq_no}] Sending request")
        st = time.time()
        response = stub.infer(request)
        et = time.time()
        logging.info(
            f"[seq_no={seq_no}] Response: data={response.data}, latency={et - st:.3f}s")
    except grpc.RpcError as e:
        logging.error(
            f"[seq_no={seq_no}] gRPC error: {e.code()} - {e.details()}")


send_inference_request(12)

