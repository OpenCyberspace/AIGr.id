import json
import time
import logging
import requests
from aios_instance import PreProcessResult, OnDataResult

logger = logging.getLogger(__name__)


class VLLMChatBlock:
    def __init__(self, context):
        """
        Initializes the chat block with vLLM server URL and settings.
        """
        self.context = context
        self.chat_sessions = {}

        self.vllm_url = context.block_init_data.get("vllm_server_url")
        if not self.vllm_url:
            raise ValueError("Missing 'vllm_server_url' in blockInitData")

        self.model_name = context.block_init_data.get(
            "model_name", "mistralai/Mistral-7B-Instruct-v0.1"
        )
        self.default_temperature = context.block_init_parameters.get("temperature", 0.7)
        self.default_max_tokens = context.block_init_settings.get("max_new_tokens", 256)

    def on_preprocess(self, packet):
        """
        Extracts input data and handles muxed inputs if needed.
        """
        try:
            data = packet.data
            if isinstance(data, str):
                data = json.loads(data)

            if "inputs" in data:
                results = [
                    PreProcessResult(packet=packet, extra_data={"input": item})
                    for item in data["inputs"]
                ]
                return True, results
            else:
                return True, [PreProcessResult(packet=packet, extra_data={"input": data})]
        except Exception as e:
            logger.error(f"[Preprocess Error] {e}")
            return False, str(e)

    def on_data(self, preprocessed_entry):
        """
        Sends a chat-style prompt to the vLLM OpenAI-compatible server.
        """
        try:
            input_data = preprocessed_entry.extra_data["input"]
            message = input_data.get("message")
            session_id = input_data.get("session_id", "default")

            # Initialize session if not exists
            if session_id not in self.chat_sessions:
                self.chat_sessions[session_id] = [
                    {"role": "system", "content": "You are a helpful assistant."}
                ]

            self.chat_sessions[session_id].append({"role": "user", "content": message})

            payload = {
                "model": self.model_name,
                "messages": self.chat_sessions[session_id],
                "temperature": self.default_temperature,
                "max_tokens": self.default_max_tokens
            }

            response = requests.post(f"{self.vllm_url}/v1/chat/completions", json=payload)
            response.raise_for_status()

            reply = response.json()["choices"][0]["message"]["content"]
            self.chat_sessions[session_id].append({"role": "assistant", "content": reply})

            return True, OnDataResult(output={"reply": reply})
        except Exception as e:
            logger.error(f"[vLLM Chat Inference Error] {e}")
            return False, str(e)

    def on_update(self, updated_parameters):
        """
        Update runtime settings like temperature or max_tokens.
        """
        try:
            if "temperature" in updated_parameters:
                self.default_temperature = updated_parameters["temperature"]
            if "max_new_tokens" in updated_parameters:
                self.default_max_tokens = updated_parameters["max_new_tokens"]
            return True, updated_parameters
        except Exception as e:
            logger.error(f"[Update Error] {e}")
            return False, str(e)

    def health(self):
        """
        Verifies if the vLLM OpenAI server is reachable.
        """
        try:
            r = requests.get(f"{self.vllm_url}/v1/models")
            return {"status": "healthy", "vllm_reachable": r.status_code == 200}
        except Exception:
            return {"status": "unreachable"}

    def management(self, action, data):
        try:
            if action == "reset":
                self.chat_sessions.clear()
                return {"message": "Chat sessions cleared"}
            return {"message": f"Unknown action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    def get_muxer(self):
        return None
