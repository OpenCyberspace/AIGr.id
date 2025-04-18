#!/bin/bash

curl -X POST -d "@./samples/filter_block.json" -H "Content-Type: application/json" \
    http://localhost:8000/api/filter