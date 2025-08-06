import grpc
from core import proxy_pb2
from core import proxy_pb2_grpc
import logging

logging.basicConfig(level=logging.INFO)

def run_inference(server_address: str, payload: bytes):
    """
    Call infer() on the gRPC server running at server_address.
    """
    try:
        # Connect to gRPC server
        channel = grpc.insecure_channel(server_address)

        metadata = [("x-service-name", "blk-dd6b6njh")]
        stub = proxy_pb2_grpc.InferenceProxyStub(channel)

        # Create request with binary data
        request = proxy_pb2.InferenceMessage(rpc_data=payload)

        logging.info(f"Sending inference request to {server_address}...")
        response = stub.infer(request, metadata=metadata)

        logging.info(f"Received response: {response.message}")
        return response.message

    except grpc.RpcError as e:
        logging.error(f"gRPC error: {e.code()} - {e.details()}")

if __name__ == "__main__":
    # Example usage
    grpc_target = "100.67.227.53:32000"  # Replace with your gateway IP and NodePort
    payload = b"example-binary-input"

    run_inference(grpc_target, payload)
