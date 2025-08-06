from llama_cpp import Llama
import logging
import time
import threading

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class LLAMAUtils:
    def __init__(self, model_path, use_gpu=False, gpu_id=0, metrics=None, model_config={}, use_native_timings=True, cleanup_config=None):
        self.model_path = model_path
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.model = None
        self.metrics = metrics
        self.model_config = model_config
        self.chat_sessions = {}
        self.use_native_timings = use_native_timings  # Flag to use llama_cpp native performance data
        # Cleanup configuration
        self.cleanup_config = cleanup_config or {
            "enabled": True,
            "check_interval": 300,  # Check every 5 minutes (in seconds)
            "session_timeout": 3600  # Remove sessions inactive for 1 hour (in seconds)
        }
        logger.info(f"\033[93mCleanup configuration: {self.cleanup_config}\033[0m")

        # Thread control
        self.cleanup_thread = None
        self.cleanup_stop_event = threading.Event()

        self.generation_config = {
            "max_tokens": 50,
            "temperature": 1.0,
            "top_p": 1.0,
            # "stop": ["Q:", "\n"]
        }

        # Start cleanup thread if enabled
        if self.cleanup_config.get("enabled", True):
            self.start_cleanup_thread()

    def start_cleanup_thread(self):
        """Start the background cleanup thread"""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.cleanup_stop_event.clear()
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                daemon=True,
                name="ChatSessionCleanup"
            )
            self.cleanup_thread.start()
            logger.info("Chat session cleanup thread started")

    def stop_cleanup_thread(self):
        """Stop the background cleanup thread"""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_stop_event.set()
            self.cleanup_thread.join(timeout=5)
            logger.info("Chat session cleanup thread stopped")

    def _cleanup_worker(self):
        """Background worker that periodically cleans up inactive sessions"""
        while not self.cleanup_stop_event.is_set():
            try:
                # Get current check_interval (allows dynamic updates)
                check_interval = self.cleanup_config.get("check_interval", 300)
                
                self._cleanup_inactive_sessions()
                
                # Wait for the next check interval or until stop event is set
                self.cleanup_stop_event.wait(check_interval)
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                # Continue running even if there's an error
                self.cleanup_stop_event.wait(30)  # Wait 30 seconds before retrying

    def _cleanup_inactive_sessions(self):
        """Clean up sessions that have been inactive for too long"""
        # Get current session_timeout (allows dynamic updates)
        session_timeout = self.cleanup_config.get("session_timeout", 3600)
        current_time = time.time()
        sessions_to_remove = []
        
        # Find sessions that need to be removed
        for session_id, session_data in self.chat_sessions.items():
            last_activity = session_data.get("timestamp_latest", 0)
            time_since_activity = current_time - last_activity
            
            if time_since_activity > session_timeout:
                sessions_to_remove.append((session_id, time_since_activity))
        
        # Remove inactive sessions
        for session_id, inactive_time in sessions_to_remove:
            try:
                logger.info(f"\033[93mRemoving inactive session: {session_id} (inactive for {inactive_time:.1f} seconds)\033[0m")
                self.remove_chat_session(session_id)
            except Exception as e:
                logger.error(f"Error removing session {session_id}: {e}")
    
        if sessions_to_remove:
            logger.info(f"\033[93mCleaned up {len(sessions_to_remove)} inactive sessions\033[0m")

    def update_cleanup_config(self, **config):
        """Update cleanup configuration at runtime and apply changes to running thread"""
        old_enabled = self.cleanup_config.get("enabled", True)
        old_check_interval = self.cleanup_config.get("check_interval", 300)
        
        # Update the configuration
        self.cleanup_config.update(config)
        
        new_enabled = self.cleanup_config.get("enabled", True)
        new_check_interval = self.cleanup_config.get("check_interval", 300)
        
        logger.info(f"Updating cleanup config: {config}")
        
        # Handle enabled/disabled state changes
        if not old_enabled and new_enabled:
            # Was disabled, now enabled - start thread
            logger.info("Enabling cleanup thread")
            self.start_cleanup_thread()
        elif old_enabled and not new_enabled:
            # Was enabled, now disabled - stop thread
            logger.info("Disabling cleanup thread")
            self.stop_cleanup_thread()
        elif old_enabled and new_enabled:
            # Was enabled and still enabled - check if we need to restart for interval change
            if old_check_interval != new_check_interval:
                logger.info(f"Check interval changed from {old_check_interval} to {new_check_interval}, restarting thread")
                self.stop_cleanup_thread()
                self.start_cleanup_thread()
            else:
                # Just session_timeout changed - no need to restart thread
                # The worker will pick up the new timeout on next check
                logger.info("Session timeout updated, will take effect on next cleanup cycle")

    def get_session_stats(self):
        """Get statistics about current sessions"""
        current_time = time.time()
        stats = {
            "total_sessions": len(self.chat_sessions),
            "session_details": []
        }
        
        for session_id, session_data in self.chat_sessions.items():
            last_activity = session_data.get("timestamp_latest", 0)
            time_since_activity = current_time - last_activity
            
            stats["session_details"].append({
                "session_id": session_id,
                "created": session_data.get("timestamp_init", 0),
                "last_activity": last_activity,
                "inactive_seconds": time_since_activity,
                "message_count": len(session_data.get("messages", []))
            })
        
        return stats

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
            
            # Pass model reference to metrics for native timing access
            if self.metrics and hasattr(self.metrics, 'set_model_reference'):
                logger.info("📊 Setting model reference in metrics for native timings")
                self.metrics.set_model_reference(self.model, self.use_native_timings)
                
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def supports_chat(self):
        return hasattr(self.model, "create_chat_completion")

    def run_inference(self, prompt, stream=False, **kwargs):
        print(f"[DEBUG] run_inference called with prompt: {prompt}")
        if not self.model:
            logger.error("Model is not loaded.")
            return None

        config = self.generation_config.copy()
        config.update(kwargs)
        print("updated config:", config)
        try:
            start_time = time.time()

            if stream:
                print("[DEBUG] stream_inference called")
                return self.stream_inference(prompt, **config)

            result = self.model(prompt, **config)
            end_time = time.time()
            print(f"[DEBUG] inference result: {result}")

            if self.metrics:
                prompt_tokens = len(self.model.tokenize(prompt))
                generated_tokens = result["usage"]["completion_tokens"]
                duration = end_time - start_time
                print(f"[DEBUG] METRICS: prompt_tokens={prompt_tokens}, generated_tokens={generated_tokens}, duration={duration}")

                try:
                    print("[DEBUG] Calling log_prompt...")
                    self.metrics.log_prompt(prompt_tokens)
                    print("[DEBUG] log_prompt completed")
                    print("[DEBUG] Calling log_response...")
                    self.metrics.log_response(generated_tokens)
                    print("[DEBUG] log_response completed")
                    print("[DEBUG] Calling observe_time_to_first_token...")
                    self.metrics.observe_time_to_first_token(start_time)
                    print("[DEBUG] observe_time_to_first_token completed")
                    print("[DEBUG] Calling observe_inference_time...")
                    self.metrics.observe_inference_time(start_time)
                    print("[DEBUG] observe_inference_time completed")
                    print("[DEBUG] Calling observe_time_per_output_token...")
                    self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                    print("[DEBUG] observe_time_per_output_token completed")
                    print("[DEBUG] Calling update_tokens_per_second...")
                    self.metrics.update_tokens_per_second(generated_tokens, duration)
                    print("[DEBUG] update_tokens_per_second completed")
                    print("[DEBUG] Updating rolling metrics for autoscaling...")
                    self.update_rolling_metrics()
                    print("[DEBUG] Rolling metrics updated")
                    print("[DEBUG] ALL METRICS CALLS COMPLETED SUCCESSFULLY")
                except Exception as metrics_error:
                    print(f"[DEBUG] METRICS ERROR in run_inference: {metrics_error}")
                    logger.error(f"❌ METRICS ERROR in run_inference: {metrics_error}")
                    import traceback
                    print(traceback.format_exc())
                    logger.error(f"   Traceback: {traceback.format_exc()}")
            return result
        except Exception as e:
            print(f"[DEBUG] Error running inference: {e}")
            logger.error(f"Error running inference: {e}")
            if self.metrics:
                print("[DEBUG] Calling increment_inference_errors due to exception...")
                try:
                    self.metrics.increment_inference_errors()
                    print("[DEBUG] increment_inference_errors completed")
                except Exception as metrics_error:
                    print(f"[DEBUG] METRICS ERROR in increment_inference_errors: {metrics_error}")
                    logger.error(f"❌ METRICS ERROR in increment_inference_errors: {metrics_error}")
            return None

    def stream_inference(self, prompt, **kwargs):
        if not self.model:
            logger.error("Model is not loaded.")
            return None

        try:
            start_time = time.time()
            first_token_time = None
            total_tokens = 0
            
            logger.info("🎬 Starting streaming inference...")
            
            for chunk in self.model(prompt, stream=True, **kwargs):
                # Track Time to First Token (TTFT)
                if first_token_time is None:
                    first_token_time = time.time()
                    if self.metrics and hasattr(self.metrics, 'observe_time_to_first_token'):
                        logger.info("⏱️ Recording TTFT for streaming")
                        try:
                            self.metrics.observe_time_to_first_token(start_time)
                            logger.info("✅ TTFT recorded successfully")
                        except Exception as ttft_error:
                            logger.error(f"❌ ERROR recording TTFT: {ttft_error}")
                
                total_tokens += 1
                yield chunk["choices"][0]["text"]
            
            # Log streaming metrics after completion
            if self.metrics:
                end_time = time.time()
                duration = end_time - start_time
                
                logger.info(f"🎬 Streaming completed - Duration: {duration:.4f}s, Tokens: {total_tokens}")
                
                try:
                    # Log basic metrics
                    prompt_tokens = len(self.model.tokenize(prompt))
                    self.metrics.log_prompt(prompt_tokens)
                    self.metrics.log_response(total_tokens)
                    
                    # Log performance metrics
                    self.metrics.observe_inference_time(start_time)
                    self.metrics.observe_time_per_output_token(start_time, total_tokens)
                    self.metrics.update_tokens_per_second(total_tokens, duration)
                    
                    # Update rolling metrics for autoscaling
                    self.update_rolling_metrics()
                    
                    logger.info("✅ Streaming metrics logged successfully")
                except Exception as metrics_error:
                    logger.error(f"❌ ERROR logging streaming metrics: {metrics_error}")
                    
        except Exception as e:
            logger.error(f"Error during streaming inference: {e}")
            if self.metrics:
                try:
                    self.metrics.increment_inference_errors()
                    logger.info("✅ Streaming error logged")
                except Exception as metrics_error:
                    logger.error(f"❌ ERROR logging streaming error: {metrics_error}")
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
                    self.metrics.observe_time_to_first_token(start_time)
                    self.metrics.observe_inference_time(start_time)
                    self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                    self.metrics.update_tokens_per_second(generated_tokens, duration)
                    
                    # Update rolling metrics for autoscaling
                    self.update_rolling_metrics()

                results.append(result)
            return results
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            if self.metrics:
                self.metrics.increment_inference_errors()
            return None

    def create_chat_session(self, session_id, system_message="", tools_list=None, tools_choice=None):
        logger.info(f"🗣️ Creating chat session: {session_id}")
        self.chat_sessions[session_id] = {
            "messages": [{
                "role": "system",
                "content": system_message
            }],
            "tools": tools_list or [],
            "tool_choice": tools_choice or {},
            "timestamp_init": time.time(),
            "timestamp_latest": time.time()
        }
        if self.metrics:
            logger.info(f"📈 Calling increase_active_sessions for session: {session_id}")
            try:
                self.metrics.increase_active_sessions()
                logger.info(f"✅ increase_active_sessions completed. Total sessions: {len(self.chat_sessions)}")
            except Exception as e:
                logger.error(f"❌ METRICS ERROR in increase_active_sessions: {e}")
        else:
            logger.warning("⚠️ No metrics object available for session tracking")

    def add_message_to_chat(self, session_id, message, role="user"):
        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")
        self.chat_sessions[session_id]["messages"].append({
            "role": role,
            "content": message
        })
        #update the timestamp for the session
        self.chat_sessions[session_id]["timestamp_latest"] = time.time()

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

    def has_chat_session(self, session_id):
        """
        Check if a chat session exists for the given session_id.
        """
        return session_id in self.chat_sessions and "messages" in self.chat_sessions[session_id]

    def run_chat_inference(self, session_id, stream, context,is_ws, **kwargs):
        print(f"[DEBUG] run_chat_inference called for session_id: {session_id}, stream={stream}")
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
            print("duration of inference:", end_time - start_time)

            if not stream:
                message = response.get("message") or response.get("choices", [{}])[0].get("message")
                if not message:
                    raise Exception("Invalid response structure")
                #print("message before adding and will be returned:", message)
                #print("message content:", message["content"])
                session["messages"].append(message)
                performance_data = self.model._ctx.get_timings()
                print(f"[DEBUG] performance_data: {performance_data}")
                if self.metrics:
                    #prompt_tokens = sum(len(self.model.tokenize(m["content"])) for m in session["messages"])
                    generated_tokens = response["usage"]["completion_tokens"]
                    duration = end_time - start_time
                    # print(f"[DEBUG] METRICS: prompt_tokens={prompt_tokens}, generated_tokens={generated_tokens}, duration={duration}")
                    try:
                        print("[DEBUG] Calling log_prompt...")
                        self.metrics.log_prompt(prompt_tokens)
                        print("[DEBUG] log_prompt completed")
                        print("[DEBUG] Calling log_response...")
                        self.metrics.log_response(generated_tokens)
                        print("[DEBUG] log_response completed")
                        print("[DEBUG] Calling observe_time_to_first_token...")
                        self.metrics.observe_time_to_first_token(start_time)
                        print("[DEBUG] observe_time_to_first_token completed")
                        print("[DEBUG] Calling observe_inference_time...")
                        self.metrics.observe_inference_time(start_time)
                        print("[DEBUG] observe_inference_time completed")
                        print("[DEBUG] Calling observe_time_per_output_token...")
                        self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                        print("[DEBUG] observe_time_per_output_token completed")
                        print("[DEBUG] Calling update_tokens_per_second...")
                        self.metrics.update_tokens_per_second(generated_tokens, duration)
                        print("[DEBUG] update_tokens_per_second completed")
                        print("[DEBUG] Updating rolling metrics for autoscaling...")
                        self.update_rolling_metrics()
                        print("[DEBUG] Rolling metrics updated")
                        print("[DEBUG] ALL METRICS CALLS COMPLETED SUCCESSFULLY")
                    except Exception as metrics_error:
                        print(f"[DEBUG] METRICS ERROR in run_chat_inference: {metrics_error}")
                        logger.error(f"❌ METRICS ERROR in run_chat_inference: {metrics_error}")
                        import traceback
                        print(traceback.format_exc())
                        logger.error(f"   Traceback: {traceback.format_exc()}")
                return message["content"]
            else:
                # Initialize an empty string to store the full response
                full_response = ""
                generated_tokens = 0
                first_token_observed = False

                # Iterate through the response
                lastchunk = None
                
                for chunk in response:
                    # Observe TTFT on the very first chunk
                    if not first_token_observed and self.metrics:
                        ttft = time.time() - start_time
                        self.metrics.observe_time_to_first_token(start_time)
                        first_token_observed = True

                    delta = chunk['choices'][0]['delta']
                    if 'content' in delta and delta['content'] is not None:
                        generated_tokens += 1
                        content_piece = delta['content']
                        
                        # Print the piece to the console in real-time
                        #print(content_piece, end="", flush=True)
                        
                        # Add the piece to our full_response string
                        full_response += content_piece
                        lastchunk = chunk
                        if is_ws:
                            context.write_ws(session_id,{"delta":content_piece})
                end_time = time.time()
                print("ttft:", ttft)
                print("eval time:", end_time - start_time)
                # get perfomance metrics
                # performance_data = self.model._ctx.get_timings()
                # print(performance_data)
 
                if lastchunk:
                    # Write the last chunk to the websocket
                    #lastchunk["choices"][0]["delta"]["content"] = "[END_OF_STREAM]"
                    lastchunk = {"delta":"[END_OF_STREAM]"}
                    if is_ws:
                        context.write_ws(session_id, lastchunk)
                print("metrics is ", self.metrics)
                performance_data = self.model._ctx.get_timings()
                print(f"[DEBUG] performance_data: {performance_data}")
                if self.metrics:
                    # Note: llama-cpp-python's response usage for streams is often incomplete.
                    # We use our own token count.

                    prompt_tokens = performance_data.get("n_p_eval", 0)
                    generated_tokens = performance_data.get("n_eval", 0)
                    duration = end_time - start_time
                    print(f"[DEBUG] METRICS (Stream): prompt_tokens={prompt_tokens}, generated_tokens={generated_tokens}, duration={duration}")
                    try:
                        print("[DEBUG] Calling log_prompt...")
                        self.metrics.log_prompt(prompt_tokens)
                        print("[DEBUG] log_prompt completed")
                        print("[DEBUG] Calling log_response...")
                        self.metrics.log_response(generated_tokens)
                        print("[DEBUG] log_response completed")
                        # TTFT is now observed when the first token arrives.
                        print("[DEBUG] Calling observe_inference_time...")
                        self.metrics.observe_inference_time(start_time)
                        print("[DEBUG] observe_inference_time completed")
                        print("[DEBUG] Calling observe_time_per_output_token...")
                        self.metrics.observe_time_per_output_token(start_time, generated_tokens)
                        print("[DEBUG] observe_time_per_output_token completed")
                        print("[DEBUG] Calling update_tokens_per_second...")
                        self.metrics.update_tokens_per_second(generated_tokens, duration)
                        print("[DEBUG] update_tokens_per_second completed")
                        print("[DEBUG] Updating rolling metrics for autoscaling...")
                        self.update_rolling_metrics()
                        print("[DEBUG] Rolling metrics updated")
                        print("[DEBUG] ALL METRICS CALLS COMPLETED SUCCESSFULLY")
                    except Exception as metrics_error:
                        print(f"[DEBUG] METRICS ERROR in run_chat_inference (stream): {metrics_error}")
                        logger.error(f"❌ METRICS ERROR in run_chat_inference (stream): {metrics_error}")
                        import traceback
                        print(traceback.format_exc())
                        logger.error(f"   Traceback: {traceback.format_exc()}")

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
            import sys
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno if tb else 'unknown'
            print(f"[DEBUG] Error during chat inference at line {line_number}: {e}")
            logger.error(f"Error during chat inference at line {line_number}: {e}")
            if self.metrics:
                self.metrics.increment_inference_errors()
            raise e

    def remove_chat_session(self, session_id):
        logger.info(f"🗑️ Removing chat session: {session_id}")
        if session_id not in self.chat_sessions:
            raise Exception(f"session_id {session_id} not found")
        del self.chat_sessions[session_id]
        if self.metrics:
            logger.info(f"📈 Calling decrease_active_sessions for session: {session_id}")
            try:
                self.metrics.decrease_active_sessions()
                logger.info(f"✅ decrease_active_sessions completed. Remaining sessions: {len(self.chat_sessions)}")
            except Exception as e:
                logger.error(f"❌ METRICS ERROR in decrease_active_sessions: {e}")
        else:
            logger.warning("⚠️ No metrics object available for session tracking")

    def update_rolling_metrics(self):
        """
        Update rolling averages for gauge metrics.
        
        This should be called periodically (e.g., every 10-30 seconds) to ensure
        rolling averages are kept up-to-date for autoscaling decisions.
        """
        if self.metrics and hasattr(self.metrics, 'update_rolling_metrics'):
            logger.info("📊 Updating rolling metrics for autoscaling")
            try:
                self.metrics.update_rolling_metrics()
                logger.info("✅ Rolling metrics updated successfully")
            except Exception as e:
                logger.error(f"❌ ERROR updating rolling metrics: {e}")
        else:
            logger.warning("⚠️ No enhanced metrics available for rolling updates")

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_cleanup_thread()
