#!/bin/bash

curl -X POST -d @./samples/create_cluster.json \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/createCluster 