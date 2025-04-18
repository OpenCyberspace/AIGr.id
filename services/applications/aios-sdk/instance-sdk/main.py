from aios_instance import Block
import os


class ExampleV1App:

    def __init__(self, block_data_full, block_init_data, block_init_settings, block_init_parameters, sessions) -> None:
        self.saved_packets = []

    def get_muxer(self):
        pass

    def on_preprocess(self, packet):

        self.saved_packets.append(packet)

        if len(self.saved_packets) == 3:
            return True, self.saved_packets

        return True, None

    def on_data(self, packet):
        return True, packet 

    def on_update(self, update_data):
        return True, "updated"

    def health(self):
        return {"healthy": True, "extra_data": []}


if __name__ == "__main__":
    block = Block(ExampleV1App)
    block.run()
