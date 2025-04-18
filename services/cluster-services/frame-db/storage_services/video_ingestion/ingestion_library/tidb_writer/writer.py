import sqlalchemy as sql
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func


import json

from .env import get_env_settings, exit_on_failure
import logging

logging = logging.getLogger("MainLogger")
env_settings = get_env_settings()

DRIVER = "mysql+pymysql"

Base = declarative_base()
Session = sessionmaker(autocommit = False)

class Frames(Base):

    __tablename__ = "frames"
    key = sql.Column(sql.String(1024), primary_key = True)                        #1KB key size max
    frame = sql.Column(sql.LargeBinary(2 * 1024 * 1024))      #upto 2MB max capacity
    frame_metadata = sql.Column(sql.LargeBinary(1024*1024))              #upto 1MB max capacity
    source_id = sql.Column(sql.String(100), nullable = True)   #upto 100 characters
    task_type = sql.Column(sql.String(10), nullable = True)  #fs redis or kafka
    worker_name = sql.Column(sql.String(50), nullable = True)
    worker_idx = sql.Column(sql.String(100), nullable = True) #upto 100 workers can run
    source_pipe = sql.Column(sql.String(50), nullable = True) #topic/queue/directory
    ext = sql.Column(sql.String(10), nullable = True)
    frame_seq_number = sql.Column(sql.Integer(), nullable = True)
    is_corrupt = sql.Column(sql.Boolean(), nullable = True)
    new_session = sql.Column(sql.Boolean(), nullable = True)

class FramesCorrupt(Base):

    __tablename__ = "corrupt_frames"

    key = sql.Column(sql.String(1024), primary_key = True)                        #1KB key size max
    frame = sql.Column(sql.LargeBinary(2 * 1024 * 1024))      #upto 2MB max capacity
    frame_metadata = sql.Column(sql.LargeBinary(1024*1024))              #upto 1MB max capacity
    source_id = sql.Column(sql.String(100), nullable = True)   #upto 100 characters
    task_type = sql.Column(sql.String(10), nullable = True)  #fs redis or kafka
    worker_name = sql.Column(sql.String(50), nullable = True)
    worker_idx = sql.Column(sql.String(100), nullable = True) #upto 100 workers can run
    source_pipe = sql.Column(sql.String(50), nullable = True)
    ext = sql.Column(sql.String(10), nullable = True)
    frame_seq_number = sql.Column(sql.Integer(), nullable = True)
    session_idx = sql.Column(sql.Integer(), nullable = True)

class DBConnector:

    @staticmethod
    def GetConnection():
        
        try:

            uri = "{}://{}@{}".format(
                    DRIVER, 
                    "root{}".format(":" + env_settings.db_settings_password if env_settings.db_settings_password else ""),
                    env_settings.destination_node
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


class FrameWriter :

    def __init__(self):
        self.engine = DBConnector.GetConnection()
        Session.configure(bind = self.engine)

        self.TableFrames = Frames
        self.TableCorruptFraes = FramesCorrupt

        Base.metadata.bind = self.engine
        Base.metadata.create_all()

        #create a session
        self.local_session = Session()

    

    def get_last_seq(self, source_id):

        result = self.local_session.query(func.count(Frames.frame_seq_number)).filter(
            Frames.source_id == source_id
        ).scalar()

        logging.info("Last sequence for source : {} is {}".format(source_id, result))

        return result

    
    def insert_to_frames(self, key : str, frame : bytes, metadata : dict, frame_meta : dict = None):
        
        try:

            frame_object = self.TableFrames(
                key = key,
                frame = frame,
                frame_metadata = json.dumps(metadata).encode('utf-8') if not frame_meta else json.dumps(frame_meta).encode('utf-8'),
                source_id = metadata['source_id'],
                task_type = metadata['task'],
                worker_name = env_settings.job_name,
                worker_idx = env_settings.worker_index,
                ext = metadata['ext'],
                source_pipe = metadata['part'],
                is_corrupt = False,
                frame_seq_number = metadata['frame_seq_number']
            )

            self.local_session.add(frame_object)
            self.local_session.commit()

            logging.info("Inserted key={} to the framedb.frames table".format(key))
            
        except Exception as e:
            logging.error(e)
            logging.error("error while inserting frame")

    def insert_to_corrupt_frames(self, key : str, frame : bytes, metadata : dict, frame_meta = None):
        try:

            frame_object = self.TableFrames(
                key = key,
                frame = frame,
                frame_metadata = json.dumps(metadata).encode('utf-8') if not frame_meta else json.dumps(frame_meta).encode('utf-8'),
                source_id = metadata['source_id'],
                task_type = metadata['task'],
                worker_name = env_settings.job_name,
                worker_idx = env_settings.worker_index,
                ext = metadata['ext'],
                source_pipe = metadata['part'],
                is_corrupt = true,
                frame_seq_number = metadata['frame_seq_number']
            )

            self.local_session.add(frame_object)
            self.local_session.commit()

            logging.info("Inserted key={} to the framedb.corrupt_frames table".format(key))

        except Exception as e:
            logging.error(e)
            logging.error("error while inserting frame")

    def exit_session(self):
        self.local_session.commit()
        self.local_session.close()

        logging.info("Closed session")
