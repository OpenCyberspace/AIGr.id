import os
import time
import logging
import torch
import json
import torch.distributed as dist
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModel, TextStreamer
from typing import Optional
from datetime import timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def safe_all_ranks(callable_fn, *args, **kwargs):

    success = torch.tensor([1], device=torch.device("cuda"))
    try:
        result = callable_fn(*args, **kwargs)
    except Exception as e:
        logger.exception(f"[RANK {dist.get_rank()}] Exception during distributed op: {e}")
        success[0] = 0
        result = None

    # Sync success status across all ranks
    dist.all_reduce(success, op=dist.ReduceOp.MIN)

    if success.item() == 0:
        logger.error(f"[RANK {dist.get_rank()}] One or more ranks failed, aborting...")
        dist.barrier()
        dist.destroy_process_group()
        raise RuntimeError("Aborted due to distributed failure")

    return result

class DistributedInferenceSDK:
    def __init__(
        self,
        model_name="microsoft/Phi-3-mini-128k-instruct",
        task="generation",
        metrics=None
    ):
        self.rank = int(os.environ.get("RANK", 0))
        self.local_rank = int(os.environ.get("LOCAL_RANK", 0))
        torch.cuda.set_device(self.local_rank)
        self.device = torch.device("cuda", self.local_rank)

        logger.info(
            f"[RANK {self.rank}] Initializing with model '{model_name}' and task '{task}'")

        if not dist.is_initialized():
            dist.init_process_group("nccl", init_method="env://", timeout=timedelta(days=30))

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            logger.info(f"[RANK {self.rank}] Pad token set to EOS token")

        self.task = task
        self.model_name = model_name
        self.metrics = metrics

        if task == "generation":
            logger.info(f"[RANK {self.rank}] Loading generation model...")
            self.model = AutoModelForCausalLM.from_pretrained(model_name, tp_plan="auto").to(self.device)
        elif task == "embedding":
            logger.info(f"[RANK {self.rank}] Loading embedding model...")
            self.model = AutoModel.from_pretrained(model_name).to(self.device)
        else:
            raise ValueError(f"Unsupported task: {task}")

        logger.info(f"[RANK {self.rank}] Model ready on device {self.device}")

        self.generation_config = {
            "max_new_tokens": 2048,
            "do_sample": True,
            "top_k": 50,
            "top_p": 0.95,
            "temperature": 1.0
        }

    def set_generation_config(self, **kwargs):
        self.generation_config.update(kwargs)


    
    def distributed_generate(self, prompt: Optional[str] = None, **kwargs):
        logger.info(f"[RANK {self.rank}] Starting distributed generation")
        if prompt is None:
            prompt = " "

        try:
            # === Step 0: Sync generation config ===
            if self.rank == 0:
                config = self.generation_config.copy()
                config.update(kwargs)
                logger.info(f"[RANK {self.rank}] Final generation config: {config}")

                config_json = json.dumps(config)
                config_bytes = config_json.encode('utf-8')
                config_tensor = torch.ByteTensor(list(config_bytes)).to(self.device)
                config_size = torch.tensor([config_tensor.numel()], dtype=torch.long, device=self.device)
                logger.info(f"[RANK {self.rank}] Broadcasting config of size {config_size.item()} bytes")
            else:
                config_size = torch.empty(1, dtype=torch.long, device=self.device)

            dist.barrier()
            safe_all_ranks(dist.broadcast, config_size, src=0)

            if self.rank != 0:
                logger.info(f"[RANK {self.rank}] Receiving config of size {config_size.item()} bytes")
                config_tensor = torch.empty(config_size.item(), dtype=torch.uint8, device=self.device)

            dist.barrier()
            safe_all_ranks(dist.broadcast, config_tensor, src=0)

            config_json = bytes(config_tensor.tolist()).decode('utf-8')
            config = json.loads(config_json)
            logger.info(f"[RANK {self.rank}] Received generation config: {config}")
            assert isinstance(config, dict), f"[RANK {self.rank}] Config deserialization failed"

            # === Step 1: Tokenize and broadcast prompt ===
            if self.rank == 0:
                encoded = self.tokenizer(prompt, return_tensors="pt", padding=False)
                input_ids = encoded["input_ids"][0].to(self.device)
                attention_mask = encoded["attention_mask"][0].to(self.device)
                prompt_len = torch.tensor([input_ids.shape[0]], dtype=torch.long, device=self.device)
                logger.info(f"[RANK {self.rank}] Broadcasting prompt of length {prompt_len.item()}")
            else:
                prompt_len = torch.empty(1, dtype=torch.long, device=self.device)

            dist.barrier()
            safe_all_ranks(dist.broadcast, prompt_len, src=0)

            if self.rank != 0:
                input_ids = torch.empty((prompt_len.item(),), dtype=torch.long, device=self.device)
                attention_mask = torch.empty((prompt_len.item(),), dtype=torch.long, device=self.device)

            dist.barrier()
            safe_all_ranks(dist.broadcast, input_ids, src=0)

            dist.barrier()
            safe_all_ranks(dist.broadcast, attention_mask, src=0)

            logger.info(f"[RANK {self.rank}] Input IDs: {input_ids.tolist()}")
            logger.info(f"[RANK {self.rank}] Attention Mask: {attention_mask.tolist()}")

            # === Step 2: Run generation ===
            logger.info(f"[RANK {self.rank}] Running model.generate with config")
            start_time = time.time()

            inputs = input_ids.unsqueeze(0).to(self.device)
            attn = attention_mask.unsqueeze(0).to(self.device)

            outputs = safe_all_ranks(self.model.generate, input_ids=inputs, attention_mask=attn, **config)
            duration = time.time() - start_time

            if outputs is None:
                return None

            logger.info(f"[RANK {self.rank}] Generation completed in {duration:.2f}s")
            logger.info(f"[RANK {self.rank}] Output IDs: {outputs[0].tolist()}")

            # === Step 3: Decode and return result ===
            if self.rank == 0:
                output_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                logger.info(f"[RANK {self.rank}] Decoded text: {output_text[:200]}...")
                self._record_metrics(input_ids.numel(), outputs.shape[-1], duration)
                return output_text

            return None

        except Exception as e:
            logger.exception(f"[RANK {self.rank}] Fatal error during distributed generation: {e}")
            dist.barrier()
            dist.destroy_process_group()
            raise RuntimeError("Aborted distributed generation due to fatal error.")

    
    def _record_metrics(self, input_tokens, output_tokens, duration):
        if self.metrics and self.rank == 0:
            self.metrics["latency"].observe(duration)
            self.metrics["tokens_in"].observe(input_tokens)
            self.metrics["tokens_out"].observe(output_tokens)
            logger.info(
                f"[RANK {self.rank}] Metrics: latency={duration:.2f}s, tokens_in={input_tokens}, tokens_out={output_tokens}")

    def _record_error(self):
        if self.metrics and self.rank == 0:
            self.metrics["errors"].inc()
            logger.info(f"[RANK {self.rank}] Metrics: error incremented")
