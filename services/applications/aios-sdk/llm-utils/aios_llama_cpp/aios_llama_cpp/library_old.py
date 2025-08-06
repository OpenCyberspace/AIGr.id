from llama_cpp import Llama
import logging
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class LLAMAUtils:
    def __init__(self, model_path, use_gpu=False, gpu_id=0, metrics=None, model_config={}):
        self.model_path = model_path
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.model = None
        self.metrics = metrics
        self.model_config = model_config
        self.chat_sessions = {}

        self.generation_config = {
            "max_tokens": 50,
            "temperature": 1.0,
            "top_p": 1.0,
            # "stop": ["Q:", "\n"]
        }

        
        

    def load_model(self):
        try:
            print(f"Loading model from {self.model_path} with config: {self.model_config}")
            self.model =  Llama(
                model_path=self.model_path,
                **self.model_config
                #n_gpu_layers=-1,
                #n_ctx=1024
                #chat_format="default"
                # use_gpu=self.use_gpu,
                # gpu_id=self.gpu_id
            )
            # print(f"Model architecture: {self.model.metadata().get('general.architecture_name', 'unknown')}")
            # print(f"Model parameters: {self.model.metadata().get('general.parameter_count', 'unknown')}")
            # print(f"Model capabilities: {self.model.metadata().get('general.capabilities', 'unknown')}")
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
        print("updated config:", config)
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
                self.metrics.observe_inference_time(duration)
                self.metrics.observe_time_per_output_token(duration, generated_tokens) #this needs to be checked later
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
                #print(chunk["choices"][0]["text"], end="", flush=True)
                yield chunk["choices"][0]["text"]
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
                    self.metrics.observe_inference_time(duration)
                    self.metrics.observe_time_per_output_token(duration, generated_tokens)
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

    def _handle_context_of_chat(self, session):
        try:
            n_ctx = self.model_config.get("n_ctx", 4096)
            safe_margin = int(0.125 * n_ctx)
            max_tokens = n_ctx - safe_margin

            #print("before",session["messages"])
            # Always keep the system prompt (index 0)
            prompt_tokens = 0
            while True:
                # Tokenize all messages except system prompt
                messages_to_check = session["messages"]
                total_tokens = sum(len(self.model.tokenize(bytes(msg['content'], "utf-8"))) for msg in messages_to_check)
                #print("total tokens:", total_tokens, "max tokens:", max_tokens)
                if total_tokens < max_tokens or len(messages_to_check) <= 1:
                    prompt_tokens = total_tokens
                    break
                # Remove oldest user/assistant message (index 1)
                session["messages"].pop(1)
            #print("after",session["messages"])
            return prompt_tokens
        except Exception as e:
            logger.error(f"Error during _handle_context_of_chat: {e}")
            if self.metrics:
                self.metrics.increment_inference_errors()
            raise

    def run_chat_inference(self, session_id, stream, context, is_ws,**kwargs):
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
            # print("kwargs for chat inference:", kwargs)
            # kwargs["max_tokens"] = 1024
            # kwargs["stop"] = ['Q:']
            # print("kwargs for chat inference: after", kwargs)
            print("kwargs for chat inference", kwargs)
            prompt_tokens = self._handle_context_of_chat(session)
            start_time = time.time()
            response = self.model.create_chat_completion(
                messages=session["messages"],
                stream=stream,
                **kwargs
            )
            end_time = time.time()

            if not stream:
                message = response.get("message") or response.get("choices", [{}])[0].get("message")
                if not message:
                    raise Exception("Invalid response structure")
                #print("message before adding and will be returned:", message)
                #print("message content:", message["content"])
                session["messages"].append(message)
                performance_data = self.model._ctx.get_timings()
                print(performance_data)
                

                if self.metrics:
                    #prompt_tokens = sum(len(self.model.tokenize(m["content"])) for m in session["messages"])
                    generated_tokens = response["usage"]["completion_tokens"]
                    duration = end_time - start_time

                    self.metrics.log_prompt(prompt_tokens)
                    self.metrics.log_response(generated_tokens)
                    self.metrics.observe_inference_time(duration)
                    self.metrics.observe_time_per_output_token(duration, generated_tokens)
                    self.metrics.update_tokens_per_second(generated_tokens, duration)

                return message["content"]
            else:
                # Initialize an empty string to store the full response
                full_response = ""

                # Iterate through the response
                lastchunk = None
                for chunk in response:
                    delta = chunk['choices'][0]['delta']
                    if 'content' in delta:
                        # Get the piece of text from the chunk
                        content_piece = delta['content']
                        
                        # Print the piece to the console in real-time
                        # print(content_piece, end="", flush=True)
                        
                        # Add the piece to our full_response string
                        full_response += content_piece
                        lastchunk = chunk
                        if is_ws:
                            context.write_ws(session_id,chunk)
                if lastchunk:
                    # Write the last chunk to the websocket
                    lastchunk["choices"][0]["delta"]["content"] = "[END_OF_STREAM]"
                    if is_ws:
                        context.write_ws(session_id, lastchunk)
                # get perfomance metrics
                performance_data = self.model._ctx.get_timings()
                print(performance_data)
                # After the loop, full_response has the complete message.
                # Now, add it to the chat history with the 'assistant' role.
                if full_response:
                    session["messages"].append({
                        "role": "assistant",
                        "content": full_response
                    })

                return full_response
        except Exception as e:
            logger.error(f"Error during chat inference: {e}")
            if self.metrics:
                self.metrics.increment_inference_errors()
            raise e

    def remove_chat_session(self, session_id):
        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")
        del self.chat_sessions[session_id]
        if self.metrics:
            self.metrics.decrease_active_sessions()
