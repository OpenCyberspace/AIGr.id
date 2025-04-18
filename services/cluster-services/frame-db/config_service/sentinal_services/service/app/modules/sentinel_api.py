from redis import sentinel
import logging

logging = logging.getLogger("MainLogger")

class SentinelApi :

    @staticmethod
    def GetSentinelConnection(host : str, port : int, password :str = None) :
        try:
            connection = sentinel.Sentinel(
                [(host, port)],
                sentinel_kwargs = {"password" : password}
            )

            return True, connection
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetMasterAddress(sentinel : sentinel.Sentinel, masterName: str) :
        try:
            master = sentinel.discover_master(masterName)
            return True, {"masterHost" : master[0], "masterPort" : master[1]}
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetSlavesAddress(sentinel : sentinel.Sentinel, masterName : str) :
        try:
            slaves = sentinel.discover_slaves(masterName)
            formattedData = []
            for slave in slaves :
                formattedData.append({
                    "slaveHost" : slave[0],
                    "slavePort" : slave[1]
                })
            
            return True, formattedData
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    @staticmethod
    def GetMasterState(sentinel : sentinel.Sentinel) :
        try:
            pass
        except Exception as e:
            logging.error(e)
            return False, str(e)