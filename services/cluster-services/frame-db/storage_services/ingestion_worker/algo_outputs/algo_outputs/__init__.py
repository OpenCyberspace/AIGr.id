import logging

from .in_memory import InMemoryAlgorithmOutputs
from .persistence import PesistentAlgorithmOutputs

logging = logging.getLogger("MainLogger")

class AlgoOutputsInterface:

    def __init__(self):
        
        self.in_memory_connector = None
        self.persistent_db_connector = None
    
    def init_memory_connector(self, destination, user, password, node, vdag, master, table_schema):
        
        self.in_memory_connector = InMemoryAlgorithmOutputs(
            destination = destination,
            username = user,
            password = password,
            node_name = node,
            vDAG_name = vdag,
            master_name = master,
            table_schema = table_schema
        )

    def init_persistent_db_connector(self, destination, user, password, node, vdag, master, table_schema):
        
        self.persistent_db_connector = PesistentAlgorithmOutputs(
            destination = destination,
            username = user,
            password = password,
            node_name = node,
            vDAG_name = vdag,
            master_name = master,
            table_schema = table_schema
        )

    def get_query_interface(self, type_ = "memory"):
        
       if type_ == "memory":

            if not self.in_memory_connector:
                return False, "in-memory connector is not initialized"
            
            return self.in_memory_connector.get_query_interface()
        
        else:
            if not self.persistent_db_connector:
                return False, "persistent connector is not initialized"
            
            return self.persistent_db_connector.get_query_interface()

    def get_schema(self, type_ = "memory"):

        if type_ == "memory":

            if not self.in_memory_connector:
                return False, "in-memory connector is not initialized"
            
            return self.in_memory_connector.get_schema()
        
        else:
            if not self.persistent_db_connector:
                return False, "persistent connector is not initialized"
            
            return self.persistent_db_connector.get_schema()

    def save_output_in_memory(self, source_id, frame_key, seq_number, outputs: dict, enable_type_check = True):

        if not self.in_memory_connector :
            return False, "in-memory connector is not initialized"
        
        return self.in_memory_connector.save_output(source_id, frame_key, seq_number, outputs, enable_type_check)
    
    def save_output_in_storage(self, source_id, frame_key, seq_number, outputs : dict, enable_type_check = True):

        if not self.persistent_db_connector:
            return False, "persistent connector is not initialized"
        
        return self.persistent_db_connector.save_output(source_id, frame_key, seq_number, outputs, enable_type_check)
    
