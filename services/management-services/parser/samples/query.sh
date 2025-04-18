#!/bin/bash

curl -X POST -d '{"query": {"reputation": {"$gt": 2}}}' \
    -H "Content-Type: application/json" \
    http://localhost:3000/clusters/query
