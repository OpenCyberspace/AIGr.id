#!/bin/bash

curl -X POST -d "@./query.json"  -H "Content-Type: application/json" \
    http://localhost:5000/clusters/query