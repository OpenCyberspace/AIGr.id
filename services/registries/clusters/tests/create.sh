#!/bin/bash

curl -X POST -d "@./create.json"  -H "Content-Type: application/json" \
    http://localhost:3000/clusters