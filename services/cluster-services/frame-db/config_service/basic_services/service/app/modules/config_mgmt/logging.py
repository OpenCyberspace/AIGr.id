from redis import Redis
import logging
logging = logging.getLogger("Mainlogging")

from datetime import datetime

from ..db.connection import FramedbConfigConnector

class LogsController :

    def __init__(self, test_mode = False, test_connection = None) :
        logging.info("Initialized LogsController")
        self.test_mode = test_mode
        self.test_connection = test_connection

        self.framedbConnector = FramedbConfigConnector()
    

    def __get_connection_from_db(self, framedb_id) :
        return self.framedbConnector.getRedisConnection(framedb_id)


    def __format_slowlogs(self, slowlog_data) :

        formatted_entries = []
        for slowlog_entry in slowlog_data :
            timestamp = datetime.fromtimestamp(int(slowlog_entry['start_time']))
            duration = slowlog_entry['duration']
            command = slowlog_entry['command']

            formatted_entries.append({"timestamp" : timestamp, "duration"  : duration, "command" : command})
        
        return formatted_entries
    

    def getSlowLog(self, framedb_id = None, n_entries = 10) :

        connection = None 
        if self.test_mode :
            connection = self.test_connection
        else :
            status, connection = self.__get_connection_from_db(framedb_id)
            if not status :
                return False, str(connection)
        
        try:

            #get slow-log data
            slowlog_data = connection.slowlog_get(n_entries)
            formatted_data = self.__format_slowlogs(slowlog_data)

            return True, slowlog_data
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
        
    def getServiceLogs(self) :
        return False, "Implement this functionality"