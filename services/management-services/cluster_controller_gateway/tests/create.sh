#!/bin/bash

curl -X POST -d "@./create.json"  -H "Content-Type: application/json" \
    http://localhost:5000/clusters/create