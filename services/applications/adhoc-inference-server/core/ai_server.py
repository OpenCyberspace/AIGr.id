import grpc
import json
from threading import Thread
import logging
import os
import uuid
import time
import copy
from flask import Flask, request, Response, jsonify

from concurrent import futures
from . import service_pb2
from . import service_pb2_grpc


from .discovery import SearchSessionsCache, DiscoveryCache, GraphCache
from .redis_cache import RedisConnectionCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resolve_graph(graph_raw, graphs_cache: GraphCache):
    try:

        graph_connections = {}
        graph_input = graph_raw

        for block_id, children in graph_input.items():
            connections = graphs_cache.resolve_outputs(block_id, children)
            graph_connections[block_id] = connections

        return graph_connections

    except Exception as e:
        raise e


class BlockInferenceServiceServicer(service_pb2_grpc.BlockInferenceServiceServicer):

    def __init__(self) -> None:
        super().__init__()
        self.sessions_client = SearchSessionsCache()
        self.discovery_cache = DiscoveryCache()
        self.connection_cache = RedisConnectionCache()
        self.graph_cache = GraphCache()

        self.adhoc_instance_id = os.getenv("ADHOC_INSTANCE_ID", "instance-0")

        self.redis_host = os.getenv("INFERENCE_REDIS_HOST", "localhost")
        self.redis_host_in_cluster = os.getenv(
            "INCLUSTER_REDIS_HOST", "localhost")

        self.redis_port = int(os.getenv("INFERENCE_REDIS_PORT", 31300))
        self.redis_port_in_cluster = int(
            os.getenv("IN_CLUSTER_REDIS_PORT", 6379))

        self.redis_host_local_ref = os.getenv(
            "INFERENCE_REDIS_INTERNAL_URL", "localhost")

        self.queue_name_prefix = f"{self.adhoc_instance_id}__"

        self.output_connection = {
            "outputs": [
                {"host": self.redis_host, "port": self.redis_port,
                    "queue_name": "OUTPUTS"}
            ]
        }

        self.output_connection_internal = {
            "outputs": [
                {"host": self.redis_host_in_cluster,
                    "port": self.redis_port_in_cluster, "queue_name": "OUTPUTS"}
            ]
        }

        self.op_connection = self.connection_cache.get(
            self.redis_host_local_ref, 6379, "")

    def process_request(self, request: service_pb2.BlockInferencePacket, extra_dict=None):
        try:

            if request.block_id == "":
                # perform similarity search:
                block_id = self.sessions_client.get_block_id(
                    request.session_id, request.query_parameters)
                request.block_id = block_id

            # get data from discovery cache:
            url, port = self.discovery_cache.discover(request.block_id)

            logger.info("block_id:{}, url={}, port={}".format(
                request.block_id, url, port))

            connection = self.connection_cache.get(url, port, request.block_id)

            if request.output_ptr == "":
                q_n = f"{self.queue_name_prefix}{request.session_id}__{request.seq_no}"
                if port != 0:
                    op_ptr = copy.deepcopy(self.output_connection_internal)
                    op_ptr['outputs'][0]['queue_name'] = q_n
                    request.output_ptr = json.dumps(op_ptr)
                else:
                    op_ptr = copy.deepcopy(self.output_connection)
                    op_ptr['outputs'][0]['queue_name'] = q_n
                    request.output_ptr = json.dumps(op_ptr)

                request_packet = service_pb2.AIOSPacket(
                    session_id=request.session_id,
                    seq_no=request.seq_no,
                    data=request.data,
                    ts=request.ts,
                    output_ptr=request.output_ptr,
                    files=request.files
                )

                logging.info(
                    f"pushing packet={request_packet.output_ptr}, {request.session_id}, {request.seq_no}")

                serialized_packet = request_packet.SerializeToString()

                connection.lpush("EXECUTOR_INPUTS", serialized_packet)

                _, result = self.op_connection.brpop(q_n)
                packet = service_pb2.AIOSPacket()
                packet.ParseFromString(result)

                if extra_dict:
                    extra_dict['model'] = block_id

                return packet
            else:
                q_n = f"{self.queue_name_prefix}{request.session_id}__{request.seq_no}"
                op_ptr = copy.deepcopy(self.output_connection)
                op_ptr['outputs'][0]['queue_name'] = q_n

                # check if it's a graph:
                output_config = json.loads(request.output_ptr)
                if 'is_graph' in output_config and output_config['is_graph']:

                    # check if the graph is compiled graph:
                    if 'is_compiled' in output_config and output_config['is_compiled']:
                        del output_config['is_compiled']
                        output_config['graph']['final'] = op_ptr
                    else:
                        resolved_graph = resolve_graph(
                            output_config['graph'], self.graph_cache)
                        output_config['graph'] = resolved_graph
                        output_config['graph']['final'] = op_ptr

                request_packet = service_pb2.AIOSPacket(
                    session_id=request.session_id,
                    seq_no=request.seq_no,
                    data=request.data,
                    ts=request.ts,
                    output_ptr=json.dumps(output_config),
                    files=request.files
                )

                logging.info(
                    f"pushing packet={request_packet.output_ptr}, {request.session_id}, {request.seq_no}")

                serialized_packet = request_packet.SerializeToString()

                connection.lpush("EXECUTOR_INPUTS", serialized_packet)

                op_connection = self.connection_cache.get(
                    self.redis_host_local_ref, 6379, "")

                _, result = op_connection.brpop(q_n)
                logger.info(f"received packed from {q_n} data: {result}")

                packet = service_pb2.AIOSPacket()
                packet.ParseFromString(result)

                if extra_dict:
                    extra_dict['model'] = block_id

                return packet

        except Exception as e:
            raise e

    def web_server(self):
        try:

            api = Flask(__name__)

            @api.route("/v1/infer", methods=['POST'])
            def v1_infer():
                try:

                    data = request.get_json()
                    model = data.get('model', '')
                    session_id = data["session_id"]
                    seq_no = data["seq_no"]
                    output_graph = data.get('graph', None)
                    model_selection = data.get('selection_query', None)
                    payload = data["data"]

                    request_packet = service_pb2.BlockInferencePacket(
                        block_id=model,
                        session_id=session_id,
                        seq_no=seq_no,
                        ts=time.time(),
                        data=json.dumps(payload),
                        output_ptr=json.dumps(
                            output_graph) if output_graph else b'',
                        query_parameters=json.dumps(
                            model_selection) if model_selection else b'',
                        frame_ptr=None,
                        files=None
                    )

                    extra_dict = {"key": "v"}

                    response = self.process_request(request_packet, extra_dict)

                    return jsonify({
                        "model": model if (model and model != '') else extra_dict.get('model', ''),
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
                    model = body.get("model", "")
                    output_graph = body.get('graph', None)
                    model_selection = body.get('selection_query', None)
                    session_id = body.get("session_id", str(uuid.uuid4()))
                    seq_no = body.get('seq_no', int(time.time() * 1000))

                    request_packet = service_pb2.BlockInferencePacket(
                        block_id=model,
                        session_id=session_id,
                        seq_no=seq_no,
                        ts=time.time(),
                        data=json.dumps(message_data),
                        output_ptr=json.dumps(
                            output_graph) if output_graph else b'',
                        query_parameters=json.dumps(
                            model_selection) if model_selection else b'',
                        frame_ptr=None,
                        files=None
                    )

                    response = self.process_request(request_packet)

                    return jsonify({
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model,
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
                    model = body.get("model", "local-model")
                    output_graph = body.get('graph', None)
                    model_selection = body.get('selection_query', None)
                    session_id = body.get("session_id", str(uuid.uuid4()))
                    seq_no = body.get("seq_no", int(time.time() * 1000))

                    request_packet = service_pb2.BlockInferencePacket(
                        block_id=model,
                        session_id=session_id,
                        seq_no=seq_no,
                        ts=time.time(),
                        data=json.dumps(prompt),
                        output_ptr=json.dumps(
                            output_graph) if output_graph else b'',
                        query_parameters=json.dumps(
                            model_selection) if model_selection else b'',
                        frame_ptr=None,
                        files=None
                    )

                    response = self.process_request(request_packet)

                    return jsonify({
                        "id": f"cmpl-{uuid.uuid4().hex}",
                        "object": "text_completion",
                        "created": int(time.time()),
                        "model": model,
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
                    block_id = request.form.get("model", "")
                    session_id = request.form["session_id"]
                    seq_no = int(request.form["seq_no"])
                    ts = float(request.form.get("ts", 0))
                    payload = request.form.get("data", "")
                    output_graph = request.form.get("output_ptr", "")
                    model_selection = request.form.get("query_parameters", "")
                    frame_ptr = request.form.get("frame_ptr", b"")

                    # Collect files
                    files_list = []
                    for key in request.files:
                        file = request.files[key]
                        metadata = request.form.get(f"{key}_metadata", "{}")
                        files_list.append(service_pb2.FileInfo(
                            metadata=metadata,
                            file_data=file.read()
                        ))

                    # Construct request packet
                    request_packet = service_pb2.BlockInferencePacket(
                        block_id=block_id,
                        session_id=session_id,
                        seq_no=seq_no,
                        ts=ts,
                        data=payload,
                        output_ptr=output_graph,
                        query_parameters=model_selection,
                        frame_ptr=frame_ptr.encode() if isinstance(frame_ptr, str) else frame_ptr,
                        files=files_list
                    )

                    # Process the packet
                    response = self.process_request(request_packet)

                    # Generate multipart response
                    boundary = f"----boundary_{uuid.uuid4().hex}"
                    parts = []

                    # Part 1: Metadata
                    metadata = {
                        "block_id": block_id,
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

                flask_thread = Thread(target=api.run, args=('0.0.0.0', 50060))
                flask_thread.daemon = True
                flask_thread.start()

            run()

        except Exception as e:
            raise e

    def infer(self, request, context):
        try:
            logger.info(
                f"Received request: session_id={request.session_id}, seq_no={request.seq_no}")

            return self.process_request(request)

        except Exception as e:
            # Handle exceptions by returning an error response
            error_message = str(e)
            logger.error(f"Error processing inference: {error_message}")

            error_response = service_pb2.AIOSPacket(
                session_id=request.session_id,
                seq_no=request.seq_no,
                data=json.dumps({"success": False, "message": error_message}),
                ts=request.ts,
                output_ptr="{}",
                files=[]
            )

            return error_response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = BlockInferenceServiceServicer()
    service_pb2_grpc.add_BlockInferenceServiceServicer_to_server(
        servicer, server)

    servicer.web_server()

    port = "50052"
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"gRPC Server started on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC Server...")
