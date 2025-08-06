#!/bin/bash

export GRPC_TRACE=api
export VDAG_URI="hello-vdag-2:0.0.1-stable"
export BLOCKS_DB_URL="http://34.58.1.86:30100"
export VDAG_DB_API_URL="http://34.58.1.86:30103"
export VDAG_ADHOC_INFERENCE_SERVER_URL="35.232.150.117:31500"
export POLICY_DB_URL="http://164.52.207.172:30102"

python3 main.py