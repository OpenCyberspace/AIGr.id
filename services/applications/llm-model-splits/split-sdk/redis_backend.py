from .distributed_sdk import CustomBackendSDK

import redis
import pickle
import time


class RedisRequest:
    def __init__(self, operation, redis_client, key, tensor, rank=None):
        self.operation = operation
        self.redis_client = redis_client
        self.key = key
        self.tensor = tensor
        self.rank = rank

    def wait(self):
        if self.operation == "send":
            # No action needed on wait for send
            return
        elif self.operation == "recv":
            for i in range(0, 5):
                time.sleep(0.01)
                break  # Small delay to avoid busy waiting


class RedisBackend(CustomBackendSDK):
    def initialize_backend(self):
        return redis.StrictRedis.from_url(self.backend_url)

    def send(self, tensor, dst, tag=0):
        key = f'{self.group_name}:send:{dst}'
        self.client.lpush(key, pickle.dumps(tensor[0].cpu().detach().numpy()))
        return RedisRequest("send", self.client, key, tensor, rank=dst)

    def recv(self, tensor, src=None, tag=0):
        key = f'{self.group_name}:send:{self.rank_id}'
        while True:
            _, data = self.client.brpop(key)
            if data:
                received_tensor = pickle.loads(data)
                tensor[0].copy_(torch.tensor(received_tensor))
                break
        return RedisRequest("recv", self.client, key, tensor, rank=src)

    def allreduce(self, tensor, op=dist.ReduceOp.SUM):
        key = f'{self.group_name}:all_reduce'
        self.client.lpush(key, pickle.dumps(tensor.cpu().numpy()))
        while self.client.llen(key) < self.world_size:
            time.sleep(0.01)
        tensors = [pickle.loads(self.client.lpop(key))
                   for _ in range(self.world_size)]
        dist_sum = sum(tensors)
        tensor.copy_(torch.tensor(dist_sum))
