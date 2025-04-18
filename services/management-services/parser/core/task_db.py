# task_db.py

import os
import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_

# Initialize the SQLAlchemy object
db = SQLAlchemy()


# Task model to store task details
class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.String(50), primary_key=True)
    status = db.Column(db.String(20), nullable=False, default='submitted')
    payload = db.Column(db.JSON, nullable=False)
    action = db.Column(db.String(50), nullable=False)
    creation_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):

        return {
            "id": self.id,
            "status": self.status,
            "payload": self.payload,
            "action": self.action,
            "creation_time": self.creation_time
        }


def init_db(app):

    db_uri = os.getenv('TASK_DB_URI', 'sqlite:///tasks.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()


def create_task(payload, action):
    task = Task(id=str(uuid.uuid4()), status="submitted",
                payload=payload, action=action)
    db.session.add(task)
    db.session.commit()
    return task.id


def get_task(task_id):
    return Task.query.get(task_id)


def update_task_status(task_id, status):
    task = get_task(task_id)
    if task:
        task.status = status
        db.session.commit()
    return task


def query_tasks(action=None, status=None, start_time=None, end_time=None):

    query = Task.query
    if action:
        query = query.filter(Task.action == action)
    if status:
        query = query.filter(Task.status == status)
    if start_time and end_time:
        query = query.filter(Task.creation_time.between(start_time, end_time))

    return [task.to_dict() for task in query.all()]
