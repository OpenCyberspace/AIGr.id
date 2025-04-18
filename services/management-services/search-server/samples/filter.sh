#!/bin/bash

curl -X POST -d "@./samples/filter.json" -H "Content-Type: application/json" \
    http://localhost:12000/api/filter-data