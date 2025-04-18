import copy
import json
from collections import defaultdict
import threading


class Muxer:
    def __init__(self, N: int):
        self.N = N
        self.store = defaultdict(list)
        self.counts = defaultdict(int)

    def process_packet(self, packet):
        if self.N == 1:
            return packet  # No merging needed

        key = (packet.session_id, packet.seq_no)
        self.store[key].append(packet)
        self.counts[key] += 1

        if self.counts[key] == self.N:
            merged_packet = self._merge_packets(self.store[key])
            del self.store[key]
            del self.counts[key]
            return merged_packet

        return None

    def _merge_packets(self, packets):
        merged_data = {"inputs": [json.loads(p.data) for p in packets]}
        merged_files = [file for p in packets for file in p.files]

        base_packet = copy.deepcopy(packets[0])
        base_packet.data = merged_data
        base_packet.files = merged_files

        return base_packet


class Batcher:
    def __init__(self, N: int):
        self.N = N
        self.batch = []

    def add_to_batch(self, packet):
        self.batch.append(packet)

        if len(self.batch) >= self.N:
            batch_copy = self.batch
            self.batch = []
            return batch_copy

        return None


class TimeBasedBatcher:
    def __init__(self, N: int, T: float, flush_callback=None):
        self.N = N
        self.T = T
        self.batch = []
        self.lock = threading.Lock()
        self.timer = None
        self.flush_callback = flush_callback

    def add_to_batch(self, packet):
        with self.lock:
            self.batch.append(packet)

            if len(self.batch) == 1:
                self._start_timer()

            if len(self.batch) >= self.N:
                return self._flush()

        return None

    def _start_timer(self):
        if self.timer is None or not self.timer.is_alive():
            self.timer = threading.Timer(self.T, self._flush_and_callback)
            self.timer.start()

    def _flush(self):
        with self.lock:
            if not self.batch:
                return None

            batch_copy = self.batch
            self.batch = []

            if self.timer:
                self.timer.cancel()
                self.timer = None

        return batch_copy

    def _flush_and_callback(self):
        batch = self._flush()
        if batch and self.flush_callback:
            self.flush_callback(batch)
