from .base import Base
from sqlalchemy import Column, ForeignKey, Integer, String, and_

from .base import db_session
import time
import uuid
import os
import requests

PARSER_SVC_API = os.getenv("PARSER_SVC_API")


class ModelTasksDB(Base):
    """Machines model."""

    __tablename__ = 'machines'

    id = Column('id', Integer, primary_key=True, doc="Id of the machine.")
    api = Column('apiRoute', String, doc="API called")
    api_method = Column('apiMethod', String, doc="GET or POST API")
    timestamp = Column('timestamp', String, doc="timestamp")
    inputs = Column('inputs', String, doc="input payload JSON string")
    intermediate_output = Column(
        'intermediateOutput', String, doc="input payload of the JSON string")
    status = Column('status', String, doc="status of the task in the DB")


class TasksDBCRUD:

    @staticmethod
    def CreateNewTask(task_data: dict):
        try:

            ts = int(time.time())
            task_data['timestamp'] = ts
            task_data['id'] = uuid.uuid4()

            task_entry = ModelTasksDB(**task_data)
            db_session.add(task_entry)

            db_session.commit()

            return True, task_data

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetTaskById(id: str):
        try:

            db_handle = db_session.Query(ModelTasksDB)
            result = db_handle.filter_by(ModelTasksDB.id == id).first()

            result = result.dict()

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def QueryTasksAPI(start_time: int, end_time: int, api: str, status: str):
        try:

            query_handle = db_session.Query(ModelTasksDB)

            # build query based on the parameter
            time_and = None

            if start_time != 0 or end_time != 0:
                time_and = and_(ModelTasksDB.timestamp >=
                                start_time, ModelTasksDB.timestamp <= end_time)

            api_and = None
            if api != "":
                if time_and:
                    api_and = and_(time_and, ModelTasksDB.api == api)
                else:
                    api_and = and_(True, ModelTasksDB.api == api)

            status_and = None
            if api_and:
                status_and = and_(api_and, ModelTasksDB.api == status)
            else:
                status_and = and_(True, ModelTasksDB.status == status)

            # perform query
            query = query_handle.filter_by(status_and)
            results = query.all()

            results_dict = []
            for result in results:
                results_dict.append(result.dict())

            return True, results_dict

        except Exception as e:
            return False, str(e)


class TasksReinstate:

    @staticmethod
    def mk_post(payload, route):
        try:
            URL = PARSER_SVC_API + route
            response = requests.post(URL, json=payload)
            if response.status_code != 200:
                raise Exception(
                    "Server error, failed to make Request code={}".format(
                        response.status_code
                    )
                )

            data = response.json()
            if data['error']:
                raise Exception(data['message'])

            return True, data['response']

        except Exception as e:
            return False, e

    @staticmethod
    def mk_get(params, route):
        try:
            URL = PARSER_SVC_API + route
            response = requests.get(URL, params=params)
            if response.status_code != 200:
                raise Exception(
                    "Server error, failed to make Request code={}".format(
                        response.status_code
                    )
                )

            data = response.json()
            if data['error']:
                raise Exception(data['message'])

            return True, data['response']

        except Exception as e:
            return False, e

    @staticmethod
    def restart_task_from_db(task_id: str):
        try:

            ret, result = TasksDBCRUD.GetTaskById(task_id)
            if not ret:
                raise Exception(result)

            if result['apiMethod'] == "GET":

                api_route = result['apiRoute']
                task_inputs = result['inputs']

                return TasksReinstate.mk_get(task_inputs, api_route)
            else:
                api_route = result['apiRoute']
                task_inputs = result['inputs']

                return TasksReinstate.mk_post(task_inputs, api_route)

        except Exception as e:
            return False, str(e)
