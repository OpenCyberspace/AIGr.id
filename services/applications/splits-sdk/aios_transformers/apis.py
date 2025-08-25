import os
from flask import Flask, request, jsonify, Response
from .sdk import DistributedInferenceSDK

# Load configuration from environment
enable_concurrency = os.getenv("ENABLE_CONCURRENCY", "false").lower() == "true"
enable_batching = os.getenv("ENABLE_BATCHING", "false").lower() == "true"
max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "4"))
batch_timeout = float(os.getenv("BATCH_TIMEOUT", "0.05"))
port = int(os.getenv("PORT", "8080"))

def main():
    sdk = DistributedInferenceSDK(
        model_name=os.getenv("MODEL_NAME", "microsoft/Phi-3-mini-128k-instruct"),
        task=os.getenv("TASK", "generation"),
    )

    if sdk.rank == 0:
        app = Flask(__name__)

        @app.route("/generate", methods=["POST"])
        def generate():
            data = request.get_json()
            prompt = data.get("prompt", "")
            gen_config = {k: v for k, v in data.items() if k != "prompt"}
            enable_streaming = gen_config.get("enable_streaming", False)

            if enable_streaming:
                def token_stream():
                    for token in sdk.distributed_generate(prompt, **gen_config):
                        yield token
                return Response(token_stream(), content_type='text/plain')
            else:
                output = sdk.distributed_generate(prompt, **gen_config)
                return jsonify({"output": output})


        @app.route("/set_config", methods=["POST"])
        def set_config():
            try:
                config = request.get_json()
                sdk.set_generation_config(**config)
                return jsonify({"message": "Generation config updated."})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        app.run(host="0.0.0.0", port=port)

    else:
        # Worker ranks must block and participate in collectives
        while True:
            sdk.distributed_generate(prompt=None)
