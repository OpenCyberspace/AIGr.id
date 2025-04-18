import torch.distributed as dist
import torch

import os
import torch
import redis
import pickle
import time
from transformers import AutoTokenizer
from pippy import schedule, pipeline
import torch.distributed as dist
from abc import ABC, abstractmethod

import torch
import pippy


class PiPPyWrapper:
    def __init__(self, model, num_stages, devices=None):
        self.model = model
        self.num_stages = num_stages
        self.devices = devices if devices else [
            torch.device(f'cuda:{i}') for i in range(num_stages)]
        self.pipeline = None

    def partition_model(self):
        self.pipeline = pippy.partition(
            self.model, self.num_stages, self.devices)
        return self.pipeline

    def run_pipeline(self, inputs):
        assert self.pipeline is not None, "Pipeline is not initialized. Call partition_model() first."
        return self.pipeline.run(inputs)

    def configure_chunks(self, chunks):
        assert self.pipeline is not None, "Pipeline is not initialized. Call partition_model() first."
        pippy.ChunkedExecution(self.pipeline, chunks=chunks)

    def save_model(self, path):
        torch.save(self.pipeline.state_dict(), path)

    def load_model(self, path):
        self.pipeline.load_state_dict(torch.load(path))

    def split_and_optimize(self, optimizer_class, lr=0.01):
        optimizers = [optimizer_class(stage.parameters(), lr=lr)
                      for stage in self.pipeline.stages()]
        return optimizers

    def sync_parameters(self):
        assert self.pipeline is not None, "Pipeline is not initialized. Call partition_model() first."
        pippy.sync_parameters(self.pipeline)

    def finalize(self):
        if self.pipeline:
            del self.pipeline


class DistributedSDK:
    def __init__(self, backend='nccl', init_method='env://', world_size=1, rank=0):
        self.backend = backend
        self.world_size = world_size
        self.rank = rank
        dist.init_process_group(
            backend=self.backend, init_method=init_method, world_size=self.world_size, rank=self.rank)
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() else 'cpu')

    def barrier(self):
        dist.barrier()

    def broadcast(self, tensor, src):
        dist.broadcast(tensor, src)
        return tensor

    def all_reduce(self, tensor, op=dist.ReduceOp.SUM):
        dist.all_reduce(tensor, op=op)
        return tensor

    def reduce(self, tensor, dst=0, op=dist.ReduceOp.SUM):
        dist.reduce(tensor, dst=dst, op=op)
        return tensor

    def gather(self, tensor, dst=0):
        gather_list = [torch.zeros_like(tensor) for _ in range(
            self.world_size)] if self.rank == dst else None
        dist.gather(tensor, gather_list, dst)
        return gather_list if self.rank == dst else None

    def scatter(self, scatter_list, src=0):
        tensor = torch.zeros_like(scatter_list[0])
        dist.scatter(tensor, scatter_list, src)
        return tensor

    def all_gather(self, tensor):
        gather_list = [torch.zeros_like(tensor)
                       for _ in range(self.world_size)]
        dist.all_gather(gather_list, tensor)
        return gather_list

    def send(self, tensor, dst):
        dist.send(tensor, dst)

    def recv(self, tensor, src):
        dist.recv(tensor, src)
        return tensor

    def reduce_scatter(self, output, input_list, op=dist.ReduceOp.SUM):
        dist.reduce_scatter(output, input_list, op=op)
        return output

    def all_to_all(self, output_list, input_list):
        dist.all_to_all(output_list, input_list)
        return output_list

    def finalize(self):
        dist.destroy_process_group()


class CustomBackendSDK(dist.ProcessGroup):
    def __init__(self, rank, world_size, backend_url, group_name='default'):
        super().__init__(rank, world_size)
        self.rank_id = rank
        self.world_size = world_size
        self.group_name = group_name
        self.backend_url = backend_url
        self.client = self.initialize_backend()

    def initialize_backend(self):
        """
        Initialize the custom backend here. This method should be 
        implemented by the subclass to connect to the desired backend.
        """
        raise NotImplementedError("Please implement this method in your subclass.")

    def send(self, tensor, dst, tag=0):
        """
        Send tensor to the destination rank.
        """
        raise NotImplementedError(
            "Please implement this method in your subclass.")

    def recv(self, tensor, src=None, tag=0):
        """
        Receive tensor from the source rank.
        """
        raise NotImplementedError(
            "Please implement this method in your subclass.")

    def allreduce(self, tensor, op=dist.ReduceOp.SUM):
        """
        Perform all-reduce operation across all ranks.
        """
        raise NotImplementedError(
            "Please implement this method in your subclass.")


class AbstractParallelSplitExecutor(ABC):
    def __init__(self, model, world_size, rank, tokenizer=None, backend=None, backend_url='redis://localhost:6379/0'):
        self.model = model
        self.world_size = world_size
        self.rank = rank
        self.tokenizer = tokenizer
        self.backend = backend
        self.split_pipeline = None
        self.stage = None

    @abstractmethod
    def initialize(self):
        """Initializes the backend and prepares the tokenizer."""
        pass

    @abstractmethod
    def prepare_inputs(self, prompts):
        """Prepares the input tensor for the model."""
        pass

    @abstractmethod
    def setup_pipeline(self, input_ids, layers_per_rank):
        """Sets up the pipeline for model inference."""
        pass

    @abstractmethod
    def load_stage(self):
        """Loads the stage of the model corresponding to the current rank."""
        pass

    @abstractmethod
    def run_pipeline(self, input_tensor):
        """Runs the inference pipeline on the input tensor."""
        pass

    @abstractmethod
    def send(self, tensor, dst):
        """Sends a tensor to another process."""
        pass

    @abstractmethod
    def recv(self, tensor, src):
        """Receives a tensor from another process."""
        pass

    @abstractmethod
    def allreduce(self, tensor):
        """Performs all-reduce operation on the tensor."""
        pass

    @abstractmethod
    def run(self, full_batch_prompts):
        """Main method that runs the model inference pipeline."""
        pass

    @abstractmethod
    def finalize(self):
        """Finalizes the process."""
        pass


class ParallelSplitExecutor:
    def __init__(self, model, world_size, rank, tokenizer=None, backend=None, backend_url='redis://localhost:6379/0'):
        self.model = model
        self.world_size = world_size
        self.rank = rank
        self.tokenizer = tokenizer or AutoTokenizer.from_pretrained(
            "Qwen/Qwen2-0.5B-Instruct")
        self.backend = backend
        self.split_pipeline = None
        self.stage = None

    def initialize(self):
        self.backend.initialize_backend()
        self.tokenizer.pad_token = self.tokenizer.eos_token

    def prepare_inputs(self, prompts):
        return self.tokenizer(prompts, return_tensors="pt", padding=True).to(torch.device("cpu"))

    def setup_pipeline(self, input_ids, layers_per_rank):
        split_spec = {
            f"model.layers.{i * layers_per_rank}": pipeline.SplitPoint.BEGINNING
            for i in range(1, self.world_size)
        }
        self.split_pipeline = pipeline.Pipeline(
            self.model, mb_args=(input_ids,), split_spec=split_spec)

    def load_stage(self):
        self.stage = self.split_pipeline.build_stage(
            self.rank, device=torch.device("cpu"))

    def run_pipeline(self, input_tensor):
        pipe_schedule = schedule.ScheduleGPipe(self.stage, chunks=4)
        return pipe_schedule.step(input_tensor)

    def send(self, tensor, dst):
        return self.backend.send(tensor, dst)

    def recv(self, tensor, src):
        return self.backend.recv(tensor, src)

    def allreduce(self, tensor):
        return self.backend.allreduce(tensor)

    def run(self, full_batch_prompts):
        inputs = self.prepare_inputs(full_batch_prompts)
        input_ids = inputs["input_ids"] if self.rank == 0 else None
        layers_per_rank = self.model.config.num_hidden_layers // self.world_size
        self.setup_pipeline(input_ids, layers_per_rank)
        self.load_stage()
        result = self.run_pipeline(input_ids if self.rank == 0 else None)
        return result

    def finalize(self):
        pass
