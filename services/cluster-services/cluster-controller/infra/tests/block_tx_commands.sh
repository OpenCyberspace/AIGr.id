#!/bin/bash

#!/bin/bash

BASE_URL="http://localhost:7500"

# Get block by ID
curl -X GET "$BASE_URL/blocks/<block_id>" -H "Content-Type: application/json"

# Get all blocks in cluster
curl -X GET "$BASE_URL/blocks" -H "Content-Type: application/json"

# Query blocks in cluster
curl -X POST "$BASE_URL/blocks/query" -H "Content-Type: application/json" -d '{"key": "value"}'

# Read cluster from environment
curl -X GET "$BASE_URL/cluster/get" -H "Content-Type: application/json"

# Query cluster
curl -X POST "$BASE_URL/cluster/query" -H "Content-Type: application/json" -d '{"query": {"key": "value"}}'

# Add a node to the cluster
curl -X POST "$BASE_URL/cluster/update/nodes" -H "Content-Type: application/json" -d '{"node": "node_data"}'

# Update cluster configuration
curl -X POST "$BASE_URL/cluster/update/config" -H "Content-Type: application/json" -d '{"config": "config_data"}'

# Update block metadata
curl -X PUT "$BASE_URL/block/update/<block_id>/metadata" -H "Content-Type: application/json" -d '{"metadata": {"key": "value"}}'

# Update block type
curl -X PUT "$BASE_URL/block/update/<block_id>/type" -H "Content-Type: application/json" -d '{"blockType": "new_type"}'

# Update block policies
curl -X PUT "$BASE_URL/block/update/<block_id>/policies" -H "Content-Type: application/json" -d '{"policies": "policy_data"}'

# Update block cluster
curl -X PUT "$BASE_URL/block/update/<block_id>/cluster" -H "Content-Type: application/json" -d '{"cluster": "cluster_data"}'

# Update block init data
curl -X PUT "$BASE_URL/block/update/<block_id>/init_data" -H "Content-Type: application/json" -d '{"blockInitData": "init_data"}'

# Update block custom metrics
curl -X PUT "$BASE_URL/block/update/<block_id>/custom_metrics" -H "Content-Type: application/json" -d '{"customMetrics": "metrics_data"}'

# Update block init settings
curl -X PUT "$BASE_URL/block/update/<block_id>/init_settings" -H "Content-Type: application/json" -d '{"initSettings": "settings_data"}'

# Update block init parameters
curl -X PUT "$BASE_URL/block/update/<block_id>/init_parameters" -H "Content-Type: application/json" -d '{"initParameters": "parameters_data"}'

# Update block parameters
curl -X PUT "$BASE_URL/block/update/<block_id>/parameters" -H "Content-Type: application/json" -d '{"parameters": "parameters_data"}'

# Update block min instances
curl -X PUT "$BASE_URL/block/update/<block_id>/min_instances" -H "Content-Type: application/json" -d '{"minInstances": "min_instances"}'

# Update block max instances
curl -X PUT "$BASE_URL/block/update/<block_id>/max_instances" -H "Content-Type: application/json" -d '{"maxInstances": "max_instances"}'

# Update block adhoc enabled
curl -X PUT "$BASE_URL/block/update/<block_id>/adhoc_enabled" -H "Content-Type: application/json" -d '{"adhocEnabled": true}'

# Update block input protocols
curl -X PUT "$BASE_URL/block/update/<block_id>/input_protocols" -H "Content-Type: application/json" -d '{"inputProtocols": "protocols_data"}'

# Update block output protocols
curl -X PUT "$BASE_URL/block/update/<block_id>/output_protocols" -H "Content-Type: application/json" -d '{"outputProtocols": "protocols_data"}'
