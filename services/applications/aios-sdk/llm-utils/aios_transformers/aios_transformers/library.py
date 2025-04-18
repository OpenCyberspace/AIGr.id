import torch
import logging
import time
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, AutoModel, Pipeline

logger = logging.getLogger(__name__)


class TransformersUtils:
    def __init__(self, model_name: str = "gpt2", device: str = None, metrics=None, tensor_parallel: bool = False, quantize: bool = False, generation_config={}):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name
        self.metrics = metrics
        self.tokenizer = None
        self.model = None
        self.generator = None
        self.chat_sessions = {}
        self.tensor_parallel = tensor_parallel
        self.quantize = quantize

        if not generation_config:
            self.generation_config = {
                "max_new_tokens": 100,
                "do_sample": True,
                "top_k": 50,
                "top_p": 0.95,
                "temperature": 1.0
            }
        else:
            self.generation_config = generation_config


    def set_generator(self, generator: Pipeline):
        self.generator = generator
        self.model = self.generator.model

    def load_model(self, extra_args: dict={}):
        model_name = self.model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        logger.info(f"Loading model {model_name} with tensor_parallel={self.tensor_parallel}...")

        load_kwargs = extra_args

        if self.tensor_parallel:
            # Multi-GPU inference via device_map
            load_kwargs.update({"device_map": "auto"})
            self.model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
        else:
            # Single-GPU inference
            self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)

        self.model.eval()  # ensure model is in inference-only mode

        # Generator uses device_map when tensor_parallel is active
        self.generator = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer
        )


    def reload_model(self):
        self.load_model(self.model_name)

    def set_generation_config(self, **kwargs):
        self.generation_config.update(kwargs)

    def generate(self, prompt: str, **kwargs):
        config = self.generation_config.copy()
        config.update(kwargs)
        try:
            start_time = time.time()
            result = self.generator(prompt, **config)
            generated_text = result[0]["generated_text"]
            end_time = time.time()

            prompt_tokens = len(self.tokenizer.encode(prompt))
            generated_tokens = len(self.tokenizer.encode(generated_text))

            if self.metrics:
                self.metrics.log_prompt(prompt_tokens)
                self.metrics.log_response(generated_tokens)
                self.metrics.observe_inference_time(start_time)
                self.metrics.observe_time_to_first_token(start_time)
                self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                self.metrics.update_tokens_per_second(generated_tokens, end_time - start_time)

            return generated_text
        except Exception as e:
            if self.metrics:
                self.metrics.increment_inference_errors()
            logger.error(f"Error generating text: {e}")
            raise

    def tokenize(self, text: str):
        return self.tokenizer(text)

    def decode(self, token_ids):
        return self.tokenizer.decode(token_ids)

    def generate_tokens(self, prompt: str, **kwargs):
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if not self.tensor_parallel:
                inputs = inputs.to(self.device)

            self.model.eval()  # double-safety

            start_time = time.time()
            tokens = self.model.generate(**inputs, **kwargs)
            end_time = time.time()

            if self.metrics:
                generated_tokens = tokens.shape[-1]
                prompt_tokens = len(inputs["input_ids"][0])
                self.metrics.log_prompt(prompt_tokens)
                self.metrics.log_response(generated_tokens)
                self.metrics.observe_inference_time(start_time)
                self.metrics.observe_time_to_first_token(start_time)
                self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                self.metrics.update_tokens_per_second(generated_tokens, end_time - start_time)

            return tokens
        except Exception as e:
            if self.metrics:
                self.metrics.increment_inference_errors()
            logger.error(f"Error generating tokens: {e}")
            raise

    def get_embeddings(self, text: str):
        try:
            load_kwargs = {"device_map": "auto"} if self.tensor_parallel else {}
            model = AutoModel.from_pretrained(self.model_name, **load_kwargs)
            model.eval()

            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            inputs = tokenizer(text, return_tensors="pt")
            if not self.tensor_parallel:
                inputs = inputs.to(self.device)

            with torch.no_grad():
                outputs = model(**inputs)
                return outputs.last_hidden_state
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            raise

    def create_chat_session(self, session_id: str, system_message: str = ""):
        self.chat_sessions[session_id] = [{"role": "system", "content": system_message}] if system_message else []
        if self.metrics:
            self.metrics.increase_active_sessions()

    def add_message_to_chat(self, session_id: str, message: str, role: str = "user"):
        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")
        self.chat_sessions[session_id].append({"role": role, "content": message})

    def run_chat_inference(self, session_id: str, **kwargs):
        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")

        try:
            history = self.chat_sessions[session_id]
            prompt = self._build_prompt(history)

            start_time = time.time()
            response = self.generate(prompt, **kwargs)
            end_time = time.time()

            self.chat_sessions[session_id].append({"role": "assistant", "content": response})

            if self.metrics:
                prompt_tokens = len(self.tokenizer.encode(prompt))
                generated_tokens = len(self.tokenizer.encode(response))
                self.metrics.log_prompt(prompt_tokens)
                self.metrics.log_response(generated_tokens)
                self.metrics.observe_inference_time(start_time)
                self.metrics.observe_time_to_first_token(start_time)
                self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                self.metrics.update_tokens_per_second(generated_tokens, end_time - start_time)

            return response
        except Exception as e:
            if self.metrics:
                self.metrics.increment_inference_errors()
            logger.error(f"Chat inference error: {e}")
            raise

    def _build_prompt(self, messages: list):
        prompt = ""
        for msg in messages:
            prompt += f"{msg['role']}: {msg['content']}\n"
        prompt += "assistant: "
        return prompt

    def remove_chat_session(self, session_id: str):
        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")
        del self.chat_sessions[session_id]
        if self.metrics:
            self.metrics.decrease_active_sessions()

    def get_device_info(self):
        return {
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
            "num_gpus": torch.cuda.device_count(),
            "tensor_parallel": self.tensor_parallel,
            "model": self.model_name
        }
