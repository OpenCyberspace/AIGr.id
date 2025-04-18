#!/bin/bash

curl -X POST -d "@./query.json"  -H "Content-Type: application/json" \
    http://localhost:3000/clusters/query