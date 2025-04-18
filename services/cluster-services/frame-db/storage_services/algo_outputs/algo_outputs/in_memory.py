import redis
import walrus
import datetime

from .utils import nested_dict_iter, to_flat_dict

from . import logging

def exit_on_error():
    exit(0)



types_mapping = {
   int : walrus.IntegerField(),
   float : walrus.FloatField(),
   str : walrus.TextField(),
   datetime.datetime : walrus.DateTimeField(),
   bytes : walrus.ByteField(),
   list : walrus.ListField(),
   bool : walrus.BooleanField()
}



class RedisConnector:
    
    @staticmethod
    def CreateConnection(self, destination : str, user : str, password : str):
        try:
            host, port = destination.split(":")
            db_connection = walrus.Database(host = host, port = port, db = 0, password = password)
            return True, db_connection
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
        

class InMemoryAlgorithmOutputs:

    def __init__(self, destination, username, password, node_name, vDAG_name, master_name, table_schema : dict):

        self.vDAG_name = vDAG_name
        self.master_name = master_name
        self.node_name = node_name

        ret, connection = RedisConnector.CreateConnection(destination, username, password)
        if not ret:
            exit_on_error()
        
        self.db_connection = connection
        self.schema = table_schema
        self.flat_schema = to_flat_dict(table_schema)

        ret, db_model = self.__create_model(schema)
        if not ret :
            exit_on_error()
        
        #save connection
        self.db_model = db_model


    def __create_model(self, schema):
        
        try:

            cols = {}

            for sc_name, sc_type in nested_dict_iter(schema, parent = ""):
                cols[sc_name] = types_mapping[sc_type]

            #create a model dynamically
            cols['key_id'] = walrus.TextField(index = True)
            cols['source_id'] = walrus.TextField(index = True)
            cols['seq_number'] = walrus.IntegerField()

            cols['db_name'] = "{}__{}__{}".format(self.master_name, self.vDAG_name, self.node_name)
            cols['__namespace__'] = self.master_name
            cols['__database__'] = self.db_connection

            NodeClass = type("BaseInMemoryObject", (walrus.Model,), cols)
            return True, NodeClass
            
        except Exception as e:
            logging.error(e)
            return False, str(e)
    
    def __validate_with_schema(self, data):

        for key in data:
            key_name, key_type = key, type(data[key])
            if key_name in self.flat_schema:
                schema_type = self.flat_schema[key_name]
                if schema_type != key_type:
                    return False
        
        else:
            return True

    def save_output(self, source_id, frame_key, seq_number, outputs: dict, enable_type_check = True):
        try:

            flat_output = to_flat_dict(outputs)
            if enable_type_check and (not self.__validate_with_schema(flat_output)):
                return False, "Validation failed"
            
            #save result
            flat_output['key_id'] = frame_key
            flat_output['source_id'] = source_id
            flat_output['seq_number'] = seq_number

            self.db_model.create(**flat_output)

            logging.info("Saved to db key={}".format(frame_key))

            return True, "Saved to db key={}".format(frame_key)
            
        except Exception as e:
            logging.error(e)
            return False, str(e)

    def get_schema(self):
        return self.schema

    def get_query_interface(self):
        return self.db_model



