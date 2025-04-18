import plyvel
from .persistence import DISK_LOADER_IMPL, DISK_WRITER_IMPL
import logging

class CorruptFrameHandler :

    @staticmethod
    def create_handle(source) :
        return DISK_WRITER_IMPL.create_db_handle(source + '-corrupt')
    

    @staticmethod
    def write_frame_to_db(handle, key : str, source : str, data : bytes) :

        logging.info(
            "Writing corrupt frame key={} source={}".format(
                key, source
            )
        )

        length = len(data)
        __len = length.to_bytes(6, byteorder = 'big')
        
        encoded_data = __len + data
        source_name = source_name + "=corrupt"

        key = "{}=={}".format(source_name, key)

        if DISK_WRITER_IMPL :
            DISK_WRITER_IMPL.write_to_disk(handle, key, encoded_data)
    
    @staticmethod
    def read_frames_by_prefix(source) :

        prefix_source = "{}=corrupt".format(source)

        for key, encoded_data in DISK_LOADER_IMPL.get_keys_by_prefix(source + '-corrupt', prefix_source) :
            __len_b = encoded_data[:6]
            length = int.from_bytes(__len_b, byteorder = "big")
            data = encoded_data[6 : 6 + length]

            key_suffix = str(key, "utf-8").split("==")[-1]
            yield (key_suffix, data)


