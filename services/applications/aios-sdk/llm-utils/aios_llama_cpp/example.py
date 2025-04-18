from aios_llama_cpp import LLAMAUtils  



# Initialize
model_path = "/home/cognitifai/Downloads/qwen1_5-0_5b-chat-q2_k.gguf"  # Update this to the real path
llama = LLAMAUtils(model_path=model_path, use_gpu=True, gpu_id=0, metrics=None)

# Load model
if llama.load_model():
    # Run basic inference
    result = llama.run_inference("What is the capital of France?")
    print("\nResult:", result["choices"][0]["text"].strip() if result else "No result")

    # Run streaming inference
    print("\nStreaming:")
    llama.run_inference("Write a haiku about space.", stream=True)

    # Chat session
    session_id = "chat123"
    llama.create_chat_session(session_id, system_message="You are a helpful assistant.")
    llama.add_message_to_chat(session_id, "What's the weather like on Mars?")
    response = llama.run_chat_inference(session_id)
    print("\n\nChat Response:", response)

    llama.remove_chat_session(session_id)
