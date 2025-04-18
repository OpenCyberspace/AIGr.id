import torch
import torch.distributed as dist
from transformers import AutoModel, AutoTokenizer
from torch.utils.data import DataLoader, Dataset
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransformersSDK:
    def __init__(self, model_path: str, device: str = 'cpu'):

        self.model_path = model_path
        self.device = torch.device(device)
        self.model = None
        self.tokenizer = None

    def load_model(self):

        try:
            logger.info("Loading model and tokenizer from path: %s",
                        self.model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModel.from_pretrained(
                self.model_path).to(self.device)
            logger.info("Model and tokenizer successfully loaded.")
        except Exception as e:
            logger.error("Failed to load model or tokenizer: %s", e)
            raise

    def offload_model(self):

        try:
            logger.info("Offloading model and tokenizer from memory.")
            self.model = None
            self.tokenizer = None
            torch.cuda.empty_cache()  # Clean up GPU memory if used
            logger.info("Model and tokenizer successfully offloaded.")
        except Exception as e:
            logger.error("Failed to offload model or tokenizer: %s", e)
            raise

    def preprocess(self, inputs: list) -> dict:

        try:
            logger.info("Preprocessing inputs for inference.")
            return self.tokenizer(inputs, padding=True, truncation=True, return_tensors="pt").to(self.device)
        except Exception as e:
            logger.error("Failed to preprocess inputs: %s", e)
            raise

    def postprocess(self, outputs) -> list:

        try:
            logger.info("Postprocessing model outputs.")
            return outputs.tolist()  # Simplified, customize as per model output type
        except Exception as e:
            logger.error("Failed to postprocess outputs: %s", e)
            raise

    def run_inference(self, inputs: list) -> list:

        if not self.model or not self.tokenizer:
            error_msg = "Model and tokenizer are not loaded. Call `load_model` first."
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            logger.info("Running inference on inputs.")
            with torch.no_grad():
                tokenized_inputs = self.preprocess(inputs)
                raw_outputs = self.model(**tokenized_inputs)
                processed_outputs = self.postprocess(raw_outputs)
            logger.info("Inference completed successfully.")
            return processed_outputs
        except Exception as e:
            logger.error("Inference failed: %s", e)
            raise

    def iterative_batched_inference(self, dataset: Dataset, batch_size: int = 32) -> list:

        try:
            logger.info(
                "Starting iterative batched inference with batch size: %d", batch_size)
            data_loader = DataLoader(dataset, batch_size=batch_size)
            all_outputs = []

            for batch in data_loader:
                batch_outputs = self.run_inference(batch)
                all_outputs.extend(batch_outputs)

            logger.info("Iterative batched inference completed successfully.")
            return all_outputs
        except Exception as e:
            logger.error("Iterative batched inference failed: %s", e)
            raise

    def load_model_on_multiple_devices(self, devices: list):

        try:
            logger.info("Loading model across multiple devices: %s", devices)
            self.model = torch.nn.DataParallel(
                self.model, device_ids=devices).to(devices[0])
            logger.info("Model successfully loaded on multiple devices.")
        except Exception as e:
            logger.error("Failed to load model on multiple devices: %s", e)
            raise

    def setup_tensor_parallel(self, devices: list):

        try:
            backend = 'gloo' if any(
                'cpu' in device for device in devices) else 'nccl'
            logger.info("Initializing process group with backend: %s", backend)
            dist.init_process_group(backend=backend)

            rank = dist.get_rank()
            device = torch.device(devices[rank % len(devices)])
            torch.cuda.set_device(device) if device.type == 'cuda' else None

            self.device = device
            self.model = self.model.to(self.device)
            self.model = torch.nn.parallel.DistributedDataParallel(
                self.model, device_ids=[self.device])
            logger.info(
                "Tensor parallel setup completed successfully on device: %s", self.device)
        except Exception as e:
            logger.error("Failed to set up tensor parallel environment: %s", e)
            raise

    def tensor_parallel_inference(self, inputs: list) -> list:

        if not self.model or not self.tokenizer:
            error_msg = "Model and tokenizer are not loaded. Call `load_model` and `setup_tensor_parallel` first."
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            logger.info("Running tensor parallel inference.")
            with torch.no_grad():
                tokenized_inputs = self.preprocess(inputs)
                raw_outputs = self.model(**tokenized_inputs)
                processed_outputs = self.postprocess(raw_outputs)

            # Collect the outputs from all processes
            gathered_outputs = [torch.zeros_like(
                processed_outputs) for _ in range(dist.get_world_size())]
            dist.all_gather(gathered_outputs, processed_outputs)

            if dist.get_rank() == 0:  # Return the results only on the master process
                logger.info(
                    "Tensor parallel inference completed successfully.")
                return [output.tolist() for output in gathered_outputs]
            else:
                return []
        except Exception as e:
            logger.error("Tensor parallel inference failed: %s", e)
            raise
