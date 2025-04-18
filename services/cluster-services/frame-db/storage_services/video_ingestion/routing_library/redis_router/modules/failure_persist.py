import os 
import plyvel
from .persistence import DISK_WRITER_IMPL, DISK_LOADER_IMPL

class EncodedDataWriter :

    @staticmethod
    def frame_encoder(frame_data : bytes, command : str) :

        length = len(frame_data)

        __len_b = length.to_bytes(6, byteorder = "big") 

        encoded_data = __len_b + frame_data + bytes(command, "utf-8")
        return encoded_data
    
    @staticmethod
    def create_db_handle(self, source, path = "/db") :
        if not DISK_WRITER_IMPL :
            logging.error("Persistence enabled, but no DISK_WRITER provided, exiting")
            os._exit(0)
        
        return DISK_WRITER_IMPL.create_db_handle(source + '-failure')

    @staticmethod
    def write_frame_to_disk(source, framedb_id, key, data, command, handle : plyvel.DB) :    
        try :
            encoded_data = LevelDBPersister.frame_encoder(data, command)
            key = "{}=={}".format(framedb_id + "=failure", key)

            #the disk writer function : write_to_disk will be called here
            DISK_WRITER.write_to_disk(handle, key, encoded_data)
            return True

        except Exception as e :
            logging.error(e)
            return False


class EncodedDataReader :

    @staticmethod
    def read_by_prefix(sourceId, framedb_name) :

        for key, encoded_data in DISK_LOADER_IMPL.get_keys_by_prefix(sourceId + "-failure", framedb_name + "=failure") :
            __len_b = encoded_data[:6]
            length = int.from_bytes(__len_b, byteorder = "big")
            data = encoded_data[6 : 6 + length]
            command = encoded_data[ (6 + length) :  ]
            command = str(command, "utf-8")

            key_suffix = str(key, "utf-8").split("==")[-1]

            yield (key_suffix, command, data)