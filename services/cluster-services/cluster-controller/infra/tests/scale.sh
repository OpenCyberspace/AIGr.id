#!/bin/bash

curl -X POST -d '{"operation": "scale", "to_scale_instances": [{"block_id": "blk-kkznb9vb"}]}' -H "Content-Type: application/json" \
    http://localhost:5000/controller/scaleInstance/cluster-123