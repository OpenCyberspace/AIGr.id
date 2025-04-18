#!/bin/bash

curl -X POST -d "@./samples/search_block.json" -H "Content-Type: application/json" \
    http://localhost:12000/api/similarity-search