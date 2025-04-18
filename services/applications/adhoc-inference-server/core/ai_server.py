import grpc
import json
import logging
import os
import copy

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
        self.redis_port = int(os.getenv("INFERENCE_REDIS_PORT", 31300))

        self.redis_host_local_ref = os.getenv(
            "INFERENCE_REDIS_INTERNAL_URL", "localhost")

        self.queue_name_prefix = f"{self.adhoc_instance_id}__"

        self.output_connection = {
            "outputs": [
                {"host": self.redis_host, "port": self.redis_port, "queue_name": "OUTPUTS"}
            ]
        }

        self.op_connection = self.connection_cache.get(
            self.redis_host_local_ref, 6379)

    def process_request(self, request: service_pb2.BlockInferencePacket):
        try:

            if request.block_id == "":
                # perform similarity search:
                block_id = self.sessions_client.get_block_id(
                    request.session_id, request.query_parameters)
                request.block_id = block_id

            # get data from discovery cache:
            public_url = self.discovery_cache.discover(request.block_id)

            connection = self.connection_cache.get(public_url, 0)

            if request.output_ptr == "":
                q_n = f"{self.queue_name_prefix}{request.session_id}__{request.seq_no}"
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
                        resolved_graph = resolve_graph(output_config['graph'], self.graph_cache)
                        output_config['graph'] = resolved_graph

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

                _, result = self.op_connection.brpop(q_n)
                packet = service_pb2.AIOSPacket()
                packet.ParseFromString(result)

                return packet

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
    service_pb2_grpc.add_BlockInferenceServiceServicer_to_server(
        BlockInferenceServiceServicer(), server)

    port = "50052"
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"gRPC Server started on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC Server...")
