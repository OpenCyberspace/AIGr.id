from aios_transformers import TransformersUtils  

# Initialize with single-GPU inference (default behavior)
utils = TransformersUtils(
    model_name="Qwen/Qwen1.5-0.5B-Chat",        # small, fast model for testing
    tensor_parallel=True     # disable multi-GPU tensor parallelism
)

utils.load_model()

# Define a simple prompt
prompt = "hey!"

# Generate text
generated = utils.generate(prompt)
print("Generated Text:\n", generated)

# Tokenize and decode for demonstration
tokens = utils.tokenize(prompt)
print("\nToken IDs:", tokens["input_ids"])

decoded = utils.decode(tokens["input_ids"][0])
print("Decoded Text:", decoded)

# Get raw token output
token_output = utils.generate_tokens(prompt, max_new_tokens=20)
print("\nGenerated Token IDs:", token_output.tolist()[0])

print(utils.get_device_info())

utils.create_chat_session('123', "You are a chat bot, you respond to only what is asked")

utils.add_message_to_chat('123', "Are you dumb?")

data = utils.run_chat_inference('123')

print(data)