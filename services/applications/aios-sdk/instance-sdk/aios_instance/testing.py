import json
import os
import time
import uuid
from urllib.parse import urlparse

from .aios_packet_pb2 import AIOSPacket, FileInfo


class TestContext:
    def __init__(self):
        self.block_data = {"block_id": os.getenv("BLOCK_ID", "test-block")}
        self.block_init_data = {}
        self.block_init_parameters = {}
        self.metrics = None
        self.sessions = None
        self.events = None


class BlockTester:
    def __init__(self, block_class):
        
        self.context = TestContext()
        self.block_instance = block_class(self.context)

    @staticmethod
    def init_with_context(block_class, context):
    
        tester = BlockTester.__new__(BlockTester)
        tester.context = context
        tester.block_instance = block_class(context)
        return tester

    def create_packet(self, data, files=None, session_id=None, seq_no=None):

        packet = AIOSPacket()
        packet.session_id = session_id or f"test-session-{uuid.uuid4()}"
        packet.seq_no = seq_no or 0
        packet.data = json.dumps(data)
        packet.ts = time.time()

        if files:
            for metadata, file_data in files:
                file_info = FileInfo()
                file_info.metadata = json.dumps(metadata)
                file_info.file_data = file_data
                packet.files.append(file_info)

        return packet

    def run(self, data, files=None):
       
        packet = self.create_packet(data=data, files=files)

        ret, preprocessed = self.block_instance.on_preprocess(packet)
        if not ret or not preprocessed:
            raise Exception(f"on_preprocess failed: {preprocessed}")

        results = []
        for entry in preprocessed:
            ret, data_result = self.block_instance.on_data(entry)
            if not ret:
                raise Exception(f"on_data failed: {data_result}")
            if data_result:
                results.append(data_result.output)

        return results
