#!/bin/bash

curl -X POST -d @./samples/vdag.json \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/createvDAG