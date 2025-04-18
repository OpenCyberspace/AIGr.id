#!/bin/bash

curl -X POST -d @./samples/allocation.json \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/createBlock 