import os
import plyvel
from .persistence import DISK_LOADER_IMPL, DISK_WRITER_IMPL
import logging

class BackPreassureHandler :

    @staticmethod
    def create_handle(source) :
        return DISK_WRITER_IMPL.create_db_handle(source + "-bp")
    
    @staticmethod
    def write_frame_to_db(handle, key : str, framedb_name : str, data : bytes, command : str) :
        logging.info(
            "Back preassure enabled, writing data to disk with key={} framedb_name={} command={}".format(
                key, framedb_name, command
            ))

        length = len(data)
        __len = length.to_bytes(6, byteorder = 'big')
        command = bytes(command, "utf-8")

        encoded_data = __len + data + command

        framedb_name = framedb_name + "=bp"

        key = "{}=={}".format(framedb_name, key)

        if DISK_WRITER_IMPL :
            DISK_WRITER_IMPL.write_to_disk(handle, key, encoded_data)
    
    @staticmethod
    def read_by_prefix(sourceId : str, framedb_name : str) :

        print(framedb_name + "=bp")

        for key, encoded_data in DISK_LOADER_IMPL.get_keys_by_prefix(sourceId + "-bp", framedb_name + "=bp") :
            __len_b = encoded_data[:6]
            length = int.from_bytes(__len_b, byteorder = "big")
            data = encoded_data[6 : 6 + length]
            command = encoded_data[ (6 + length) :  ]
            command = str(command, "utf-8")

            key_suffix = str(key, "utf-8").split("==")[-1]

            yield (key_suffix, command, data)