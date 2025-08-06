import grpc
import logging
import json
import uuid
from concurrent import futures
import time
from threading import Thread
from flask import Flask, jsonify, Response, request

from . import vdag_service_pb2
from . import vdag_service_pb2_grpc
from .adhoc_inference_server_client import AdhocInferenceClient
from .system import vDAGAPIServer

from .env import Env
from .system import vDAG, block_to_vdag, vdag_to_block

from .health_checker import HealthChecker
from .quality_checker import QualityChecker, QualityCheckerManagementServer
from .quota_checker import QuotaManager, QuotaManagerAPIServer
from .metrics import AIOSMetrics
# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class vDAGInferenceServiceServicer(vdag_service_pb2_grpc.vDAGInferenceServiceServicer):

    def __init__(self) -> None:
        super().__init__()

        # load env, vdag object and caching
        self.env = Env()
        self.vdag = vDAG(self.env)

        # init quota config and health checker:
        self.metrics = AIOSMetrics(self.vdag.vdag_uri)
        self.metrics.register_counter("inference_requests_total", "Total inference requests processed")
        self.metrics.register_gauge("inference_fps", "Frames per second (FPS) of inference")
        self.metrics.register_gauge("inference_latency_seconds", "Current latency per inference request")

        self.vdag_api = vDAGAPIServer(self.vdag)

        # prepare all policies
        self.quota_checker = QuotaManager(self.vdag.vdag_data, self.env.vdag_custom_init_data)
        self.quality_checker = QualityChecker(self.vdag.vdag_data, self.env.vdag_custom_init_data)
        self.health_checker = HealthChecker(self.vdag.vdag_data, self.vdag_api.app, self.env.vdag_custom_init_data)

        # quota checker APIs:
        self.quota_checker_apis = QuotaManagerAPIServer(
            self.quota_checker.quota_cache, self.quality_checker, self.vdag_api.app
        )

        self.quality_checker_apis = QualityCheckerManagementServer(
            qa=self.quality_checker, app=self.vdag_api.app
        )

        # run the server in a thread
        self.vdag_api.run_in_thread()

        self.vdag_serialized_l3_graph = json.dumps(self.vdag.get_l3_graph())
        self.vdag_serialized_l2_graph = json.dumps(self.vdag.get_graph_format())
        self.head = self.vdag.head_block_id

        self.adhoc_inference_client = AdhocInferenceClient(
            self.env.adhoc_inference_server_uri
        )

        self.metrics.start_metrics_http_server()

    def web_server(self):
        try:

            api = Flask(__name__)

            @api.route("/v1/infer", methods=['POST'])
            def v1_infer():
                try:

                    data = request.get_json()
                    session_id = data["session_id"]
                    seq_no = data["seq_no"]
                    payload = data["data"]

                    request_packet = vdag_service_pb2.vDAGInferencePacket(
                        session_id=session_id,
                        seq_no=seq_no,
                        ts=time.time(),
                        data=json.dumps(payload),
                        frame_ptr=None,
                        files=None
                    )

                    response = self.infer_no_ctx(request_packet)

                    return jsonify({
                        "session_id": response.session_id,
                        "seq_no": response.seq_no,
                        "ts": response.ts,
                        "data": json.loads(response.data),
                    })

                except Exception as e:
                    return jsonify({"success": False, "message": str(e)})

            @api.route("/v1/chat/completions", methods=["POST"])
            def chat_completions():
                try:
                    body = request.get_json()
                    message_data = body.get("messages", [])
                    session_id = body.get("session_id", str(uuid.uuid4()))
                    seq_no = body.get('seq_no', int(time.time() * 1000))

                    request_packet = vdag_service_pb2.vDAGInferencePacket(
                        session_id=session_id,
                        seq_no=seq_no,
                        ts=time.time(),
                        data=json.dumps(message_data),
                        frame_ptr=None,
                        files=None
                    )

                    response = self.infer_no_ctx(request_packet)

                    return jsonify({
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": json.loads(response.data) if response.data.startswith('{') else response.data
                                },
                                "finish_reason": "stop"
                            }
                        ]
                    })

                except Exception as e:
                    return jsonify({
                        "error": {
                            "message": str(e),
                            "type": "internal_error",
                            "param": None,
                            "code": 500
                        }
                    }), 500

            @api.route("/v1/completions", methods=["POST"])
            def completions():
                try:
                    body = request.get_json()

                    prompt = body.get("prompt", "")        
                    session_id = body.get("session_id", str(uuid.uuid4()))
                    seq_no = body.get("seq_no", int(time.time() * 1000))

                    request_packet = vdag_service_pb2.vDAGInferencePacket(
                        session_id=session_id,
                        seq_no=seq_no,
                        ts=time.time(),
                        data=json.dumps(prompt),
                        frame_ptr=None,
                        files=None
                    )

                    response = self.infer_no_ctx(request_packet)

                    return jsonify({
                        "id": f"cmpl-{uuid.uuid4().hex}",
                        "object": "text_completion",
                        "created": int(time.time()),
                        "choices": [
                            {
                                "text": json.loads(response.data) if response.data.startswith('{') else response.data,
                                "index": 0,
                                "logprobs": None,
                                "finish_reason": "stop"
                            }
                        ]
                    })

                except Exception as e:
                    return jsonify({
                        "error": {
                            "message": str(e),
                            "type": "internal_error",
                            "param": None,
                            "code": 500
                        }
                    }), 500

            @api.route("/v1/infer-multipart", methods=["POST"])
            def v1_infer_multipart():
                try:
                    # Form fields
                    session_id = request.form["session_id"]
                    seq_no = int(request.form["seq_no"])
                    ts = float(request.form.get("ts", 0))
                    payload = request.form.get("data", "")
                    frame_ptr = request.form.get("frame_ptr", b"")

                    # Collect files
                    files_list = []
                    for key in request.files:
                        file = request.files[key]
                        metadata = request.form.get(f"{key}_metadata", "{}")
                        files_list.append(vdag_service_pb2.vDAGFileInfo(
                            metadata=metadata,
                            file_data=file.read()
                        ))

                    # Construct request packet
                    request_packet = vdag_service_pb2.vDAGInferencePacket(
                        session_id=session_id,
                        seq_no=seq_no,
                        ts=ts,
                        data=payload,
                        frame_ptr=frame_ptr.encode() if isinstance(frame_ptr, str) else frame_ptr,
                        files=files_list
                    )

                    # Process the packet
                    response = self.infer_no_ctx(request_packet)

                    # Generate multipart response
                    boundary = f"----boundary_{uuid.uuid4().hex}"
                    parts = []

                    # Part 1: Metadata
                    metadata = {
                        "session_id": response.session_id,
                        "seq_no": response.seq_no,
                        "ts": response.ts
                    }
                    parts.append(
                        f"--{boundary}\r\n"
                        "Content-Type: application/json\r\n"
                        'Content-Disposition: form-data; name="metadata"; filename="metadata.json"\r\n\r\n'
                        f"{json.dumps(metadata)}\r\n"
                    )

                    # Part 2: Response Data
                    try:
                        parsed_data = json.loads(response.data)
                    except Exception:
                        parsed_data = {"raw": response.data}

                    parts.append(
                        f"--{boundary}\r\n"
                        "Content-Type: application/json\r\n"
                        'Content-Disposition: form-data; name="data"; filename="data.json"\r\n\r\n'
                        f"{json.dumps(parsed_data)}\r\n"
                    )

                    # Part 3+: Attach response files
                    for i, f in enumerate(response.files):
                        parts.append(
                            f"--{boundary}\r\n"
                            "Content-Type: application/octet-stream\r\n"
                            f'Content-Disposition: attachment; name="file{i}"; filename="file{i}.bin"\r\n\r\n'
                        )
                        parts.append(f.file_data)

                    # Final boundary
                    parts.append(f"--{boundary}--\r\n")

                    # Construct raw multipart body
                    body = b""
                    for part in parts:
                        if isinstance(part, str):
                            body += part.encode("utf-8")
                        else:
                            body += part + b"\r\n"

                    return Response(
                        body,
                        status=200,
                        content_type=f"multipart/mixed; boundary={boundary}"
                    )

                except Exception as e:
                    return jsonify({"success": False, "message": str(e)}), 500

            def run():
                # api.run(host='0.0.0.0', port=50060)

                flask_thread = Thread(target=api.run, args=('0.0.0.0', 50052))
                flask_thread.daemon = True
                flask_thread.start()

            run()

        except Exception as e:
            raise e

    def infer_no_ctx(self, request):
        try:

            if not self.quota_checker.check_quota(request.session_id, request):
                return vdag_service_pb2.vDAGInferencePacket(
                    session_id=request.session_id,
                    data=json.dumps({"success": False, "message": "quota management policy did not allow this request"})
                )


            logging.info(f"Received inference request for session: {request.session_id}")
            start_time = time.time()  # Start latency measurement

            # Perform inference logic
            block_request = vdag_to_block(request, self.head, self.vdag_serialized_l2_graph, self.vdag.vdag_uri)
            block_response = self.adhoc_inference_client.infer(request.session_id, block_request)

            logging.info(f"Received response: {block_response}")
            vdag_response = block_to_vdag(block_response)

            # Record metrics
            self.metrics.increment_counter("inference_requests_total")
            latency = time.time() - start_time  # Calculate latency
            self.metrics.set_gauge("inference_latency_seconds", latency)  # Update latest latency

            # Estimate FPS (assuming one request = one frame)
            fps = 1 / latency if latency > 0 else 0
            self.metrics.set_gauge("inference_fps", fps)

            if self.quality_checker.policy:
                self.quality_checker.submit_for_quality_check({
                    "request": request,
                    "response": vdag_response
                })

            return vdag_response

        except Exception as e:
            logging.error(f"Error processing inference request: {str(e)}", exc_info=True)
            return vdag_service_pb2.vDAGInferencePacket()

    def infer(self, request, context):
        try:

            if not self.quota_checker.check_quota(request.session_id, request):
                return vdag_service_pb2.vDAGInferencePacket(
                    session_id=request.session_id,
                    data=json.dumps({"success": False, "message": "quota management policy did not allow this request"})
                )

            logging.info(f"Received inference request for session: {request.session_id}")
            start_time = time.time()  # Start latency measurement

            # Perform inference logic
            block_request = vdag_to_block(request, self.head, self.vdag_serialized_l2_graph, self.vdag.vdag_uri)
            block_response = self.adhoc_inference_client.infer(request.session_id, block_request)

            logging.info(f"Received response: {block_response}")
            vdag_response = block_to_vdag(block_response)

            # Record metrics
            self.metrics.increment_counter("inference_requests_total")
            latency = time.time() - start_time  # Calculate latency
            self.metrics.set_gauge("inference_latency_seconds", latency)  # Update latest latency

            # Estimate FPS (assuming one request = one frame)
            fps = 1 / latency if latency > 0 else 0
            self.metrics.set_gauge("inference_fps", fps)

            if self.quality_checker.policy:
                self.quality_checker.submit_for_quality_check({
                    "request": request,
                    "response": vdag_response
                })

            return vdag_response

        except Exception as e:
            logging.error(f"Error processing inference request: {str(e)}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error.")
            return vdag_service_pb2.vDAGInferencePacket()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    servicer = vDAGInferenceServiceServicer()
    servicer.web_server()
    vdag_service_pb2_grpc.add_vDAGInferenceServiceServicer_to_server(servicer, server)
    server.add_insecure_port('[::]:50051')
    logging.info("Starting vDAGInferenceService server on port 50051...")
    server.start()
    server.wait_for_termination()
