import os
import torch
import torch.nn as nn
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransformersSplitInference:
    def __init__(self, model_split_path: str, device: str = 'cpu'):

        self.model_split_path = model_split_path
        self.device = torch.device(device)
        self.model_split = None
        self.tokenizer = None

    def load_split(self):

        try:
            logger.info("Loading model split from path: %s",
                        self.model_split_path)
            self.model_split = torch.load(
                self.model_split_path, map_location=self.device)
            logger.info("Model split successfully loaded.")
        except Exception as e:
            logger.error("Failed to load model split: %s", e)
            raise

    def offload_split(self):

        try:
            logger.info("Offloading model split from memory.")
            self.model_split = None
            torch.cuda.empty_cache()  # Clean up GPU memory if used
            logger.info("Model split successfully offloaded.")
        except Exception as e:
            logger.error("Failed to offload model split: %s", e)
            raise

    def preprocess(self, inputs: list) -> dict:

        try:
            logger.info("Preprocessing inputs for inference.")
            return self.tokenizer(inputs, padding=True, truncation=True, return_tensors="pt").to(self.device)
        except Exception as e:
            logger.error("Failed to preprocess inputs: %s", e)
            raise

    def postprocess(self, outputs) -> torch.Tensor:

        try:
            logger.info("Postprocessing model split outputs.")
            return outputs
        except Exception as e:
            logger.error("Failed to postprocess outputs: %s", e)
            raise

    def run_inference(self, input_tensor: torch.Tensor) -> torch.Tensor:

        if not self.model_split:
            error_msg = "Model split is not loaded. Call `load_split` first."
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            logger.info("Running inference on input tensor.")
            with torch.no_grad():
                output_tensor = self.model_split(input_tensor)
            logger.info("Inference completed successfully.")
            return self.postprocess(output_tensor)
        except Exception as e:
            logger.error("Inference with model split failed: %s", e)
            raise


class TorchModelSplit:
    def __init__(self, model_path: str, output_dir: str, device: str = 'cpu'):

        self.model_path = model_path
        self.output_dir = output_dir
        self.device = torch.device(device)
        self.model = None

    def load_from_hugging_face(self):
        try:

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path, map_location=self.device
            )
            logger.info("Model successfully loaded.")
        except Exception as e:
            logger.error("Failed to load model: %s", e)
            raise

    def load_model(self):
        """
        Load the entire model from the file.
        """
        try:
            logger.info("Loading model from path: %s", self.model_path)
            self.model = torch.load(self.model_path, map_location=self.device)
            logger.info("Model successfully loaded.")
        except Exception as e:
            logger.error("Failed to load model: %s", e)
            raise

    def split_model(self, split_config: dict) -> list:

        try:
            if not self.model:
                raise ValueError("Model not loaded. Call `load_model` first.")

            logger.info(
                "Splitting the model as per the provided configuration.")

            # Example split configuration: {'split_1': [0, 4], 'split_2': [4, 8], 'split_3': [8, 12]}
            splits = []
            layers = list(self.model.encoder.layer)
            for split_name, (start, end) in split_config.items():
                split_model = nn.Sequential(*layers[start:end])
                splits.append((split_name, split_model))
                logger.info("Generated model split: %s", split_name)

            logger.info("Model successfully split.")
            return splits
        except Exception as e:
            logger.error("Failed to split model: %s", e)
            raise

    def save_split(self, split_name: str, split_model: nn.Module):

        try:
            split_path = os.path.join(self.output_dir, f"{split_name}.pt")
            torch.save(split_model, split_path)
            logger.info("Saved model split: %s", split_path)
        except Exception as e:
            logger.error("Failed to save model split %s: %s", split_name, e)
            raise

    def generate_single_split(self, start: int, end: int) -> nn.Module:

        try:
            if not self.model:
                raise ValueError("Model not loaded. Call `load_model` first.")

            logger.info(
                "Generating single model split from layers %d to %d", start, end)
            layers = list(self.model.encoder.layer)
            split_model = nn.Sequential(*layers[start:end])
            logger.info("Successfully generated single model split.")
            return split_model
        except Exception as e:
            logger.error("Failed to generate single model split: %s", e)
            raise

    def load_model_split(self, split_name: str) -> nn.Module:

        try:
            split_path = os.path.join(self.output_dir, f"{split_name}.pt")
            logger.info("Loading model split from path: %s", split_path)
            model_split = torch.load(split_path, map_location=self.device)
            logger.info("Model split %s successfully loaded.", split_name)
            return model_split
        except Exception as e:
            logger.error("Failed to load model split %s: %s", split_name, e)
            raise

    def run_inference_on_split(self, split_name: str, inputs: list) -> torch.Tensor:

        try:
            # Load the split model
            split_model = self.load_model_split(split_name)

            # Initialize TransformersSplitInference with the split model
            split_inference = TransformersSplitInference(
                model_split_path='', device=self.device)
            split_inference.model_split = split_model

            # Pre-process inputs
            input_tensor = split_inference.preprocess(inputs)

            # Run inference
            output_tensor = split_inference.run_inference(input_tensor)

            return output_tensor
        except Exception as e:
            logger.error(
                "Failed to run inference on model split %s: %s", split_name, e)
            raise
