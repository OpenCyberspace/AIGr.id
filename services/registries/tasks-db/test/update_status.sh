#!/bin/bash

curl -X POST "http://localhost:8000/task_update" \
     -H "Content-Type: application/json" \
     -d '{
           "task_id": "ad7cc06a-0c4c-4aad-aacc-7759e420c24f",
           "status": "completed",
           "task_status_data": {"result": "Task finished successfully"}
         }'
