#!/bin/bash

curl -X POST http://$CLUSTER_CONTROLLER_GATEWAY_URL/vdag-controller/cluster-123 \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_controller",
    "payload": {
      "vdag_controller_id": "estimator-001",
      "vdag_uri": "pose-estimator:v0.0.1-stable",
      "config": {
        "policy_execution_mode": "local",
        "replicas": 2
      }
    }
  }'