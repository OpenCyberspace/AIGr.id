import grpc
import time
import json
from core import service_pb2
from core import service_pb2_grpc

SERVER_ADDRESS = "localhost:50052"

def create_chat_request():
    """Creates an inference request for LLM chat with history using query_parameters."""

    # Example chat message with previous history
    data_json = json.dumps({
        "task": "llm_chat",
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "Hello! How are you?"},
            {"role": "assistant", "content": "I'm doing well! How can I assist you today?"},
            {"role": "user", "content": "Tell me about black holes."}
        ]
    })

    # Query parameters for selecting the block dynamically - similarity search data
    query_parameters_json = json.dumps({
        "body": {
            "values": {
                "matchType": "cluster",
                "rankingPolicyRule": {
                    "values": {
                        "executionMode": "code",
                        "policyRuleURI": "simple_selector:1.0-stable",
                        "settings": {},
                        "parameters": {
                            "filterRule": {
                                "matchType": "block",
                                "filter": {
                                    "blockQuery": {
                                                "variable": "id",
                                                "operator": "==",
                                                "value": "blk-dd6b6njh"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    })

    request = service_pb2.BlockInferencePacket(
        session_id="sess-12345",  # Unique session ID
        seq_no=1,  # First message in sequence
        data=data_json,  # Chat messages history
        ts=time.time(),  # Current timestamp
        query_parameters=query_parameters_json,  # Block selection logic
        output_ptr="",  # No graph inference
        files=[]  # No files attached
    )

    return request

def main():

    # Create a gRPC channel and stub
    channel = grpc.insecure_channel(SERVER_ADDRESS)
    stub = service_pb2_grpc.BlockInferenceServiceStub(channel)

    # Create and send the request
    request = create_chat_request()
    response = stub.infer(request)

    # Print the response
    print("Inference Response:")
    print("Session ID:", response.session_id)
    print("Sequence No:", response.seq_no)
    print("Data:", response.data)
    print("Timestamp:", response.ts)

if __name__ == "__main__":
    main()
