import grpc
from . import proxy_pb2
from . import proxy_pb2_grpc


class InferenceProxyClient:
    def __init__(self, url, block_id):
        self.channel = grpc.insecure_channel(url)
        self.block_id = block_id
        self.stub = proxy_pb2_grpc.InferenceProxyStub(self.channel)

    def infer(self, rpc_data):
        request = proxy_pb2.InferenceMessage(rpc_data=rpc_data)
        metadata = [('x-service-name', self.block_id)]
        response = self.stub.infer(request, metadata=metadata)
        return response.message

    def lpush(self, queue_name, rpc_data):
        self.infer(rpc_data)
