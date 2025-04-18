#!/bin/bash

curl -X POST -d '{"operation": "downscale", "to_remove_instances": ["in-okl9"], "block_id": "blk-kkznb9vb"}' -H "Content-Type: application/json" \
    http://localhost:5000/controller/scaleInstance/cluster-123