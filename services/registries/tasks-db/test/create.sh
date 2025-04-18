#!/bin/bash

curl -X POST "http://localhost:8000/task" \
     -H "Content-Type: application/json" \
     -d '{
           "task_type": "classification",
           "task_data": {"input": "some data"},
           "task_status": "pending"
         }'
