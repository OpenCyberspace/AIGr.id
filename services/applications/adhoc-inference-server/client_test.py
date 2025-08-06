import grpc
import json
import service_pb2
import service_pb2_grpc
import time

SERVER_ADDRESS = "localhost:50052"


def run():
    # Connect to the gRPC server
    channel = grpc.insecure_channel("35.232.150.117:31500")
    #channel = grpc.insecure_channel(SERVER_ADDRESS)
    stub = service_pb2_grpc.BlockInferenceServiceStub(channel)

    # Example file metadata and binary data
    file_info = service_pb2.FileInfo(
        metadata=json.dumps({"filename": "example.txt", "size": 123}),
        file_data=b"Example file content"
    )

    '''output_ptr = {
            "is_graph": True,
            "graph": {
                "hello-multi-001": ["hello-multi-002"],
                "hello-multi-002": ["hello-multi-003"],
                "hello-multi-003": []
            }
        }'''

    # Create the BlockInferencePacket request
    request = service_pb2.BlockInferencePacket(
        block_id="magistral-small-2506-llama-cpp-block",
        session_id="chat-002",
        seq_no=10,
        frame_ptr=b"",  # Empty bytes for now
        data=json.dumps({"type": "chat", "message": "What is your name?"}),
        query_parameters="",
        ts=1234567890.0,
        files=[file_info],  # Attach the file
        output_ptr=b''
    )

    try:

        st = time.time()
        # Make the gRPC call
        response = stub.infer(request)

        et = time.time()


        print("\n=== Response Received ===")
        print(f"Latency: {et - st}s")
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
