import sqlalchemy as sql
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, mapper, create_session
from sqlalchemy import func
import datetime

from . import logging

from .utils import nested_dict_iter, to_flat_dict

DRIVER = "mysql+pymysql"

def exit_on_failure():
    exit(0)


class NodeOutputObject:
    pass

types_mapping = {
    int : sql.Integer,
    str : sql.Text,
    bool : sql.Boolean,
    bytes : sql.LargeBinary,
    float : sql.Float,
    list : sql.ARRAY,
    datetime.datetime : sql.DateTime
}

class DBConnector:

    @staticmethod
    def GetConnection(env_settings : dict):
        
        try:

            uri = "{}://{}@{}".format(
                    DRIVER, 
                    "root{}".format(":" + env_settings['username'] if 'password' in env_settings else ""),
                    env_settings['destination_node']
            )

            logging.info("Connecting to {}".format(uri))
            uri_db = "{}/{}".format(uri, env_settings.db_name)
            engine = sql.create_engine(uri_db)
            if not database_exists(engine.url):
                create_database(engine.url)

            logging.info("Successfully connected to database")
            return engine

        except Exception as e:
            raise e
            logging.error(e)
            logging.error("failed to connect to database")
            exit_on_failure()


class PesistentAlgorithmOutputs:

    def __init__(self, destination, username, password, node_name, vDAG_name, master_name, table_schema : dict):

        self.db_connection = DBConnector.GetConnection({"username" : username, "password" : password, 'destination_node' : destination})
        self.metadata = sql.MetaData(bind = self.db_connection)

        self.node_name = node_name
        self.vDAG_name = vDAG_name
        self.master_name = master_name

        self.table_name = "{}__{}__{}".format(master_name, vDAG_name, node_name)

        ret, table_model = self.__create_model(table_schema)

        if not table_model:
            logging.error("failed to table schema")
            exit_on_failure()

        self.schema = table_schema
        self.flat_schema = to_flat_dict(table_schema)

        #map table to model
        self.metadata.create_all()

        #mapping
        mapper(NodeOutputObject, table_model)

        self.table_model = table_model

        #create a session
        self.session = create_session(bind=self.db_connection, autocommit=False, autoflush=True)


    def get_schema(self):
        return self.schema

    def get_query_interface(self):
        return self.session.query

    def execute_string_query(self, query_string):
        try:

            #execute query string
            with self.db_connection.connect() as connection:
                rs = connection.execute(query_string)
                return True, rs
            
        except Exception as e:
            logging.error(e)
            return False, str(e)

    def save_output(self, source_id, frame_key, seq_number, outputs: dict, enable_type_check = True):
        
        try:

            outputs_flat = to_flat_dict(outputs)

            #validate with flat-schema
            if enable_type_check and (not self.__validate_with_schema(outputs_flat)):
                return False, "Validation failed"
            
            outputs_flat['key_id']  = frame_key
            outputs_flat['source_id'] = source_id
            outputs_flat['seq_number'] = seq_number

            output_object = NodeOutputObject(**outputs_flat)

            self.session.add(output_object)
            self.session.commit()

            logging.info9("Saved to db key={}".format(frame_key))

            return True, "Saved to db key={}".format(frame_key)
            
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

    def __create_model(self, schema):

        try:

            cols = []

            keys = [(k, v) for k, v in nested_dict_iter(schema, parent = "")]

            for sc in schema:
                sc_name, sc_type = sc

                col_type = types_mapping[sc_name]
                cols.append(sql.Column(sc_name, col_type))
            

            #append primary key and other custom columns
            pk = sql.Column('key_id', sql.String(1024), primary_key = True)
            source_id = sql.Column('source_id', sql.String(1024))
            seq_number = sql.Column('seq_number', sql.Integer)
            
            cols.extend([pk, seq_number, source_id])

            table = sql.Table(self.table_name, self.metadata, *cols)
            return True, table
            
        except Exception as e:
            logging.error(e)
            return False, str(e)