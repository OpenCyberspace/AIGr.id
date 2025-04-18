import grpc
import json
from core import service_pb2
from core import service_pb2_grpc

def run():
    """Test the gRPC server with a sample request."""
    # Connect to the gRPC server
    channel = grpc.insecure_channel("localhost:50052")
    stub = service_pb2_grpc.BlockInferenceServiceStub(channel)

    # Example file metadata and binary data
    file_info = service_pb2.FileInfo(
        metadata=json.dumps({"filename": "example.txt", "size": 123}),
        file_data=b"Example file content"
    )

    output_ptr = {
            "is_graph": True,
            "graph": {
                "blk-ksshxpiy": {
                    "outputs": [
                        {"host": "localhost", "port": 6379, "queue_name": "blk-bfl3gbd5_inputs"}
                    ]
                },
                "blk-bfl3gbd5": {
                    "outputs": [
                        {"host": "localhost", "port": 6379, "queue_name": "blk-tsonq3qr_inputs"}
                    ]
                },
                "blk-tsonq3qr": {
                    "outputs": []
                }
            }
        }

    # Create the BlockInferencePacket request
    request = service_pb2.BlockInferencePacket(
        block_id="blk-ksshxpiy",
        session_id="session_123",
        seq_no=1,
        frame_ptr=b"",  # Empty bytes for now
        data=json.dumps({"hey": "you"}),
        query_parameters=json.dumps({"param1": "value1", "param2": "value2"}),
        ts=1234567890.0,
        files=[file_info],  # Attach the file
        output_ptr=json.dumps(output_ptr)
    )

    try:
        # Make the gRPC call
        response = stub.infer(request)
        print("\n=== Response Received ===")
        print(f"Session ID: {response.session_id}")
        print(f"Sequence No: {response.seq_no}")
        print(f"Data: {response.data}")
        print(f"Timestamp: {response.ts}")
        print(f"Output Ptr: {response.output_ptr}")
        print(f"Files Received: {len(response.files)}")

        # Parse JSON response data
        try:
            response_data = json.loads(response.data)
            print(f"Parsed Response: {response_data}")
        except json.JSONDecodeError:
            print("Response data is not a valid JSON string.")

    except grpc.RpcError as e:
        print(f"gRPC Error: {e.code()} - {e.details()}")

if __name__ == "__main__":
    run()
