import grpc
from . import proxy_pb2
from . import proxy_pb2_grpc


class InferenceProxyClient:
    def __init__(self, url):
        self.channel = grpc.insecure_channel(url)
        self.stub = proxy_pb2_grpc.InferenceProxyStub(self.channel)

    def infer(self, rpc_data):
        request = proxy_pb2.InferenceMessage(rpc_data=rpc_data)
        response = self.stub.infer(request)
        return response.message

    def lpush(self, queue_name, rpc_data):
        self.infer(rpc_data)
