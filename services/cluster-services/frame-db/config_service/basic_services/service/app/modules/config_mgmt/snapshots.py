import redis
import logging

logging = logging.getLogger("MainLogger")

from ..db.connection import FramedbConfigConnector
from ..db.save_config import ConfigSaver


class BackupsAndSnapshotController :

    def __init__(self, test_mode = False, test_connection = None) :
        logging.info("Initialized BackupsAndSnapshotController")
        self.test_connection = test_connection
        self.test_mode = True
        self.framedbConnector = FramedbConfigConnector()

    def __get_connection_from_db(self, framedb_id) :
        return self.framedbConnector.getRedisConnection(framedb_id)
    

    def __save_to_db(self, framedb_id, parameter, value) :

        ret, result = ConfigSaver().updateConfig(
            framedb_id, 
            parameter,
            str(value)
        )

        if not ret :
            return False, str(result)
        return True, "config updated and saved to db"

        
    def setBackupConfig(self, framedb_id, interval, n_keys_changed) :
        connection = None 
        if self.test_mode and self.test_connection :
            connection = self.test_connection
        else :
            status, connection = self.__get_connection_from_db(framedb_id)
            if not status :
                return False, str(connection)
        
        try:
            save_string = "{} {}".format(interval, n_keys_changed)
            result = connection.config_set("save", save_string)
            if result :
                ret, result = self.__save_to_db(framedb_id, "save", save_string)
                if not ret :
                    return False, str(e)
                return True, "Interval updated successfully"
            return False, "Interval update failed"
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    def setRDBFileName(self, framedb_id, backupFileName) :
        connection = None 
        if self.test_mode and self.test_connection :
            connection = self.test_connection
        else :
            status, connection = self.__get_connection_from_db(framedb_id)
            if not status :
                return False, str(connection)
        
        try:
            filename = backupFileName.split("/")[-1]
            path = backupFileName.split("/")[:-1]

            fp_path = "".join(path)
            if backupFileName.startswith('/') :
                fp_path = '/' + fp_path
            if fp_path != "" :
                connection.config_set("dir", fp_path)

            result = connection.config_set("dbfilename", filename)
            if result :
                return True, "RDB filename updated successfully"
            return False, "RDB filename update failed"
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    def getBackupConfig(self, framedb_id) :

        connection = None 
        if self.test_mode and self.test_connection :
            connection = self.test_connection
        else :
            status, connection = self.__get_connection_from_db(framedb_id)
            if not status :
                return False, str(connection)

        try:
            result = {}
            save_config = connection.config_get("save")['save']
            save_config = save_config.split(" ")

            result['snapshot_intervals'] = []
            for i in range(0, len(save_config) - 1):
                interval, n_keys = save_config[i], save_config[i + 1]
                result['snapshot_intervals'].append({"time_s" : interval, "keys_changed" : n_keys})
            
            result['dbfilename'] = connection.config_get('dbfilename')['dbfilename']
            result['rdb_parameters'] = connection.config_get("rdb*")
            result['backup_path'] = connection.config_get("dir")['dir']

            return True, result
 
        except Exception as e:
            logging.error(e)
            return False, str(e)
        
    
    def takeSnapshot(self,framedb_id,  as_file = None) :
        connection = None 
        if self.test_mode and self.test_connection :
            connection = self.test_connection
        else :
            status, connection = self.__get_connection_from_db(framedb_id)
            if not status :
                return False, str(connection)
        
        try:
            previous_file_name = None
            fp_dir = None
            if as_file:
                #previous file :
                previous_file_name = connection.config_get('dbfilename')['dbfilename']
                fp_dir = connection.config_get('dir')['dir']

                filename = as_file.split("/")[-1]
                path = as_file.split("/")[:-1]

                fp_path = "".join(path)
                if as_file.startswith('/') :
                    fp_path = '/' + fp_path 
                if fp_path != "" :
                    connection.config_set("dir", fp_path)

                connection.config_set('dbfilename', filename)
            
            result = connection.bgsave()
            if not result :
                return False, "Failed to create snapshot"
            #restore the previous filename
            if previous_file_name :
                connection.config_set("dir", fp_dir)
                connection.config_set("dbfilename", previous_file_name)
            
            return True, "Scheduled background saving in background"

        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    def setRDBChecksum(self, framedb_id, enable) :
        connection = None 
        if self.test_mode and self.test_connection :
            connection = self.test_connection
        else :
            status, connection = self.__get_connection_from_db(framedb_id)
            print(connection)
            if not status :
                return False, str(connection)
        
        try:
            result = connection.config_set("rdbchecksum", "yes" if enable else "no")
            if result :
                ret, result = self.__save_to_db(framedb_id, "rdbchecksum", "yes" if enable else "no")
                if not ret :
                    return False, str(result)
                return True, "RDB checksum updated successfully"
            return False, "RDB checksum update failed"
        except Exception as e:
            logging.error(e)
            return False, str(e)
        

    def setRDBCompression(self, framedb_id, enable) :
        connection = None 
        if self.test_mode and self.test_connection :
            connection = self.test_connection
        else :
            status, connection = self.__get_connection_from_db(framedb_id)
            if not status :
                return False, str(connection)
        
        try:
            result = connection.config_set("rdbcompression", "yes" if enable else "no")
            if result :
                ret, result = self.__save_to_db(framedb_id, "rdbcompression", "yes" if enable else "no")
                return True, "Interval updated successfully"
            return False, "RDB compression update failed"
        except Exception as e:
            logging.error(e)
            return False, str(e)


