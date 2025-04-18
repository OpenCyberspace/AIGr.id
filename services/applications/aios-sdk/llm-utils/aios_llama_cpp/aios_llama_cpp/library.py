from llama_cpp import Llama
import logging
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class LLAMAUtils:
    def __init__(self, model_path, use_gpu=False, gpu_id=0, metrics=None):
        self.model_path = model_path
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.model = None
        self.metrics = metrics
        self.chat_sessions = {}

        self.generation_config = {
            "max_tokens": 50,
            "temperature": 1.0,
            "top_p": 1.0,
            "stop": ["Q:", "\n"]
        }

    def load_model(self):
        try:
            self.model = Llama(
                model_path=self.model_path,
                use_gpu=self.use_gpu,
                gpu_id=self.gpu_id
            )
            logger.info("Model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def supports_chat(self):
        return hasattr(self.model, "create_chat_completion")

    def run_inference(self, prompt, stream=False, **kwargs):
        if not self.model:
            logger.error("Model is not loaded.")
            return None

        config = self.generation_config.copy()
        config.update(kwargs)

        try:
            start_time = time.time()

            if stream:
                return self.stream_inference(prompt, **config)

            result = self.model(prompt, **config)
            end_time = time.time()

            if self.metrics:
                prompt_tokens = len(self.model.tokenize(prompt))
                generated_tokens = result["usage"]["completion_tokens"]
                duration = end_time - start_time

                self.metrics.log_prompt(prompt_tokens)
                self.metrics.log_response(generated_tokens)
                self.metrics.observe_inference_time(start_time)
                self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                self.metrics.update_tokens_per_second(generated_tokens, duration)

            return result
        except Exception as e:
            logger.error(f"Error running inference: {e}")
            if self.metrics:
                self.metrics.increment_inference_errors()
            return None

    def stream_inference(self, prompt, **kwargs):
        if not self.model:
            logger.error("Model is not loaded.")
            return None

        try:
            for chunk in self.model(prompt, stream=True, **kwargs):
                print(chunk["choices"][0]["text"], end="", flush=True)
        except Exception as e:
            logger.error(f"Error during streaming inference: {e}")
            if self.metrics:
                self.metrics.increment_inference_errors()
            return None

    def tokenize(self, text):
        if not self.model:
            logger.error("Model is not loaded.")
            return None
        try:
            return self.model.tokenize(text)
        except Exception as e:
            logger.error(f"Error tokenizing text: {e}")
            return None

    def detokenize(self, tokens):
        if not self.model:
            logger.error("Model is not loaded.")
            return None
        try:
            return self.model.detokenize(tokens)
        except Exception as e:
            logger.error(f"Error detokenizing tokens: {e}")
            return None

    def save_model(self, save_path):
        if not self.model:
            logger.error("Model is not loaded.")
            return False
        try:
            self.model.save(save_path)
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def get_model_info(self):
        if not self.model:
            logger.error("Model is not loaded.")
            return None
        try:
            return self.model.get_model_info()
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None

    def set_seed(self, seed):
        if not self.model:
            logger.error("Model is not loaded.")
            return False
        try:
            self.model.set_seed(seed)
            return True
        except Exception as e:
            logger.error(f"Error setting seed: {e}")
            return False

    def generate_text(self, prompt, num_sequences=1, **kwargs):
        if not self.model:
            logger.error("Model is not loaded.")
            return None

        config = self.generation_config.copy()
        config.update(kwargs)

        try:
            results = []
            for _ in range(num_sequences):
                start_time = time.time()
                result = self.model(prompt, **config)
                end_time = time.time()

                if self.metrics:
                    prompt_tokens = len(self.model.tokenize(prompt))
                    generated_tokens = result["usage"]["completion_tokens"]
                    duration = end_time - start_time

                    self.metrics.log_prompt(prompt_tokens)
                    self.metrics.log_response(generated_tokens)
                    self.metrics.observe_inference_time(start_time)
                    self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                    self.metrics.update_tokens_per_second(generated_tokens, duration)

                results.append(result)
            return results
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            if self.metrics:
                self.metrics.increment_inference_errors()
            return None

    def create_chat_session(self, session_id, system_message="", tools_list=None, tools_choice=None):
        self.chat_sessions[session_id] = {
            "messages": [{
                "role": "system",
                "content": system_message
            }],
            "tools": tools_list or [],
            "tool_choice": tools_choice or {}
        }
        if self.metrics:
            self.metrics.increase_active_sessions()

    def add_message_to_chat(self, session_id, message, role="user"):
        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")
        self.chat_sessions[session_id]["messages"].append({
            "role": role,
            "content": message
        })

    def run_chat_inference(self, session_id, **kwargs):
        if not self.model:
            raise Exception("Model is not loaded")

        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")

        if not self.supports_chat():
            raise Exception("Chat mode is not supported by this model")

        try:
            session = self.chat_sessions[session_id]
            if session["tools"]:
                kwargs["tools"] = session["tools"]
            if session["tool_choice"]:
                kwargs["tool_choice"] = session["tool_choice"]

            start_time = time.time()
            response = self.model.create_chat_completion(
                messages=session["messages"],
                **kwargs
            )
            end_time = time.time()

            message = response.get("message") or response.get("choices", [{}])[0].get("message")
            if not message:
                raise Exception("Invalid response structure")

            session["messages"].append(message)

            if self.metrics:
                prompt_tokens = sum(len(self.model.tokenize(m["content"])) for m in session["messages"])
                generated_tokens = response["usage"]["completion_tokens"]
                duration = end_time - start_time

                self.metrics.log_prompt(prompt_tokens)
                self.metrics.log_response(generated_tokens)
                self.metrics.observe_inference_time(start_time)
                self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                self.metrics.update_tokens_per_second(generated_tokens, duration)

            return message["content"]

        except Exception as e:
            logger.error(f"Error during chat inference: {e}")
            if self.metrics:
                self.metrics.increment_inference_errors()
            raise

    def remove_chat_session(self, session_id):
        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")
        del self.chat_sessions[session_id]
        if self.metrics:
            self.metrics.decrease_active_sessions()
