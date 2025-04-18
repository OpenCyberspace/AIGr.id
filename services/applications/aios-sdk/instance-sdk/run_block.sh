#!/bin/bash

block_id=$1
mgmt_port=$2
m_port=$3

docker run -d --net=host --rm --env="BLOCK_ID=$block_id" \
    --env="MGMT_PORT=$mgmt_port" \
    --env="METRICS_PORT=$m_port" \
    --name="$block_id" \
    aios-instance:v1