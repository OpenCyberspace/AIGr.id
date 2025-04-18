#!/bin/bash

# Usage:
# ./install_inference_server.sh <ADHOC_INSTANCE_ID> <CLUSTER_PUBLIC_IP> <DB_HOST> <DB_PORT> <DB_USER>

ADHOC_INSTANCE_ID=$1
CLUSTER_PUBLIC_IP=$2
DB_HOST=$3
DB_PORT=$4
DB_USER=$5

if [ -z "$ADHOC_INSTANCE_ID" ] || [ -z "$CLUSTER_PUBLIC_IP" ] || [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_USER" ]; then
  echo "Usage: $0 <ADHOC_INSTANCE_ID> <CLUSTER_PUBLIC_IP> <DB_HOST> <DB_PORT> <DB_USER>"
  exit 1
fi

NAMESPACE="inference-server"

echo "Creating namespace if not exists..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

echo "Deploying inference-server..."

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-server
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: inference-server
  template:
    metadata:
      labels:
        app: inference-server
    spec:
      containers:
        - name: inference-server
          image: aiosv1/inference-server:v1
          ports:
            - containerPort: 50052
            - containerPort: 20000
          env:
            - name: DB_PASSWORD
              value: ""
            - name: INFERENCE_REDIS_CONNECTION_URL
              value: "$CLUSTER_PUBLIC_IP"
            - name: ADHOC_INSTANCE_ID
              value: "$ADHOC_INSTANCE_ID"
            - name: BLOCKS_URL
              value: "http://blocks-db-svc.registries.svc.cluster.local:3001"
            - name: DB_NAME
              value: ""
            - name: QUEUE_DEFAULT_URL
              value: ""
            - name: SEARCH_SERVER_API_URL
              value: "http://search-server.utils.svc.cluster.local:12000"
            - name: INFERENCE_REDIS_INTERNAL_URL
              value: "redis.inference-server.svc.cluster.local"
            - name: DB_HOST
              value: "$DB_HOST"
            - name: DB_PORT
              value: "$DB_PORT"
            - name: DB_USER
              value: "$DB_USER"
            - name: INSTANCE_BLOCK_DEFAULT_URL
              value: ""
            - name: BLOCKS_DB_URL
              value: "http://blocks-db-svc.registries.svc.cluster.local:3001"
            - name: DISCOVERY_MODE
              value: "gateway"
---
apiVersion: v1
kind: Service
metadata:
  name: inference-server
  namespace: $NAMESPACE
spec:
  selector:
    app: inference-server
  ports:
    - name: grpc
      protocol: TCP
      port: 50052
      targetPort: 50052
      nodePort: 31500
    - name: rest
      protocol: TCP
      port: 20000
      targetPort: 20000
      nodePort: 31501
  type: NodePort
EOF

echo "inference-server deployed successfully in namespace '$NAMESPACE'"
