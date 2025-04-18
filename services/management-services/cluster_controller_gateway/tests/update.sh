#!/bin/bash

curl -X PUT -d "@./update.json"  -H "Content-Type: application/json" \
    http://localhost:5000/clusters/update/cluster-x2