#!/bin/bash

set -e

# Ensure jq is available
if ! command -v jq &> /dev/null; then
  echo "jq not found. Installing..."
  apt update && apt install -y jq curl
fi

# Collect GPU info using nvidia-smi
output=$(/usr/bin/nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits \
  | jq -R -s -c 'split("\n")[:-1] 
                 | map(split(", ")) 
                 | map({modelName: .[0], memory: (.[1] | tonumber)})')

# Get the node name from the host's hostname
node_name=$HOSTNAME

echo "Annotating node: $node_name"
echo "GPU Info: $output"

# Annotate the node with GPU data
/usr/bin/kubectl annotate node "$node_name" gpu.aios/info="$output" --overwrite

echo "Annotation complete."
