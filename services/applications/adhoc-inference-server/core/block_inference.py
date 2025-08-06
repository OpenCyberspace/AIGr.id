import grpc
from . import service_pb2
from . import service_pb2_grpc


class BlockInferenceClient:
    def __init__(self, host='0.0.0.0', port=50051):
        # Create a channel and a stub (client)
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = service_pb2_grpc.AIServiceStub(self.channel)

    def infer(self, session_id, seq_no, frame_ptr, data, ts, is_frame, block_id):
        # Create a request message
        request = service_pb2.AIOSPacket(
            session_id=session_id,
            seq_no=seq_no,
            frame_ptr=frame_ptr,
            data=data,
            ts=ts,
            is_frame=is_frame
        )

        # Make the call
        metadata = [('x-service-name', block_id)]
        response = self.stub.infer(request)

        return response

    def close(self):
        # Close the channel
        self.channel.close()


class PersistentBlockInferenceClient:
    def __init__(self):
        self.clients = {}

    def get_client(self, session_id, host='localhost', port=50051):
        if session_id not in self.clients:
            self.clients[session_id] = BlockInferenceClient(host, port)
        return self.clients[session_id]

    def infer(self, session_id, seq_no, frame_ptr, data, ts, is_frame):
        client = self.get_client(session_id)
        return client.infer(session_id, seq_no, frame_ptr, data, ts, is_frame)

    def close(self):
        for client in self.clients.values():
            client.close()
        self.clients.clear()

    def close_connection(self, session_id):
        if session_id in self.clients:
            self.clients[session_id].close()
