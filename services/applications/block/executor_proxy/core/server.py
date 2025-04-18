import redis
import logging
import grpc
from concurrent import futures


from . import proxy_pb2_grpc
from . import proxy_pb2

logging.basicConfig(level=logging.DEBUG)


class InferenceProxy(proxy_pb2_grpc.InferenceProxyServicer):

    def __init__(self) -> None:
        super().__init__()
        self.internal_connector = redis.Redis(
            host='localhost', port=6379
        )

    def infer(self, request, context):
        try:
            self.internal_connector.lpush("EXECUTOR_INPUTS", request.rpc_data)
            return proxy_pb2.InferenceRespose(message=True)
        except Exception as e:
            logging.error(f"failed to process inference request: {e}")
            self.internal_connector = redis.Redis(host='localhost', port=6379)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    proxy_pb2_grpc.add_InferenceProxyServicer_to_server(InferenceProxy(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("InferenceProxy gRPC Server started on port 50051...")
    server.wait_for_termination()
