import plyvel
import os


class DiskLoaderImpl :
    
    @staticmethod
    def get_keys_by_prefix(sourceId : str, framedb_id : str) :
        path = os.path.join(os.curdir, "db", sourceId)

        db_path = os.path.join(path)
        if not os.path.exists(db_path) :
            return

        #create db_handle :
        db_handle = plyvel.DB(db_path, create_if_missing = True)

        print(db_handle)

        for key, data in db_handle.iterator(prefix = bytes(framedb_id, "utf-8")) :
            db_handle.delete(key)
            yield (key, data)
        
        db_handle.close()


class DiskWriterImpl :

    @staticmethod
    def write_to_disk(db_handle : plyvel.DB, composite_key : str, encoded_data : bytes) :

        key = bytes(composite_key, "utf-8")
        db_handle.put(key, encoded_data)
    

    @staticmethod
    def create_db_handle(source : str) :

        path = os.path.join(os.curdir, "db")

        if not os.path.exists(path) :
            os.mkdir(path)
        
        db_path = os.path.join(path, source)
        return plyvel.DB(db_path, create_if_missing = True)
    
    @staticmethod
    def close_handler(handle : plyvel.DB) :

        handle.close()
    

DISK_LOADER_IMPL = DiskLoaderImpl 
DISK_WRITER_IMPL = DiskWriterImpl    
