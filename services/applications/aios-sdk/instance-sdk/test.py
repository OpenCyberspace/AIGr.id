import redis
import os
import json
import time

from proto.aios_packet_pb2 import AIOSPacket


class RedisTestClient:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_client = redis.StrictRedis(
            host=self.redis_host, port=self.redis_port, decode_responses=False)

    def send_test_packet(self, i):
        packet = AIOSPacket()
        packet.session_id = "test_session"
        packet.seq_no = i
        packet.data = b"test data"
        packet.ts = time.time()

        # Example file metadata and binary data
        file_info = packet.files.add()
        file_info.metadata = json.dumps({"filename": "test.txt", "size": 1024})
        file_info.file_data = b"test file data"

        # Example output_ptr JSON
        output_ptr = {
            "is_graph": True,
            "graph": {
                "blk-ksshxpiy": {
                    "outputs": [
                        {"host": "localhost", "port": 6379, "queue_name": "blk-bfl3gbd5_inputs"}
                    ]
                },
                "blk-bfl3gbd5": {
                    "outputs": [
                        {"host": "localhost", "port": 6379, "queue_name": "blk-tsonq3qr_inputs"}
                    ]
                },
                "blk-tsonq3qr": {
                    "outputs": []
                },
                "final": {
                    "outputs": [
                        {"host": "localhost", "port": 6379, "queue_name": "OUTPUTS"}
                    ]
                }
            }
        }
        packet.output_ptr = json.dumps(output_ptr)

        serialized_packet = packet.SerializeToString()
        self.redis_client.lpush("EXECUTOR_INPUTS", serialized_packet)
        print("Test packet sent to Redis queue: INPUTS")

        # _, op_data = self.redis_client.brpop("OUTPUTS")
        # packet = AIOSPacket()
        # packet.ParseFromString(op_data)

        # print(packet)


if __name__ == "__main__":

    #packet = AIOSPacket()
    #packet.ParseFromString(b"\n\x0ctest_session\x10\x12\"\x17{\"output\": \"my output\"})\x9f+,\xcf\xc7\xed\xd9A:8\n&{\"filename\": \"test.txt\", \"size\": 1024}\x12\x0etest file data")
    #print(packet)

    client = RedisTestClient()

    i = 0

    for i in range(0, 20):
        i += 1
        client.send_test_packet(i)

    while True:
        _, outputs = client.redis_client.brpop("OUTPUTS")
        packet = AIOSPacket()
        packet.ParseFromString(outputs)
        print(packet)
