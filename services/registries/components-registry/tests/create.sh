#!/bin/bash

curl -X POST http://192.168.111.111:32000/cr/api/registerComponent -d @sample.json \
    --header "Content-Type: application/json"
