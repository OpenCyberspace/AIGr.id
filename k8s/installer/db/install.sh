#!/bin/bash

# USAGE: ./deploy_registry_fixed.sh <replica-count> [storage-size]
REPLICAS=$1
STORAGE=${2:-1Gi}
NAMESPACE="registries"

if [[ -z "$REPLICAS" ]]; then
  echo "Usage: $0 <replica-count> [storage-size]"
  exit 1
fi

echo "Deploying $REPLICAS MongoDB replica nodes with $STORAGE storage each in namespace '$NAMESPACE'..."

# Create namespace
kubectl --insecure-skip-tls-verify create namespace $NAMESPACE --dry-run=client -o yaml | kubectl --insecure-skip-tls-verify apply -f -

# Step 1: Create PVs, PVCs, Deployments, and Services per replica
for i in $(seq 0 $((REPLICAS - 1))); do
  echo "🔧 Setting up registry-$i..."

  # Create PersistentVolume
  cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: registry-pv-$i
  labels:
    volume-id: registry-$i
spec:
  capacity:
    storage: $STORAGE
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  hostPath:
    path: /mnt/data/registry-$i
  persistentVolumeReclaimPolicy: Retain
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: registry
              operator: In
              values:
                - "yes"
EOF

  # Create PersistentVolumeClaim
  cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: registry-pvc-$i
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  volumeName: registry-pv-$i
  resources:
    requests:
      storage: $STORAGE
EOF

  # Create Deployment
  cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registry-$i
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: registry-$i
  template:
    metadata:
      labels:
        app: registry-$i
    spec:
      #affinity:
      #  nodeAffinity:
      #    requiredDuringSchedulingIgnoredDuringExecution:
      #      nodeSelectorTerms:
      #        - matchExpressions:
      #            - key: registry
      #              operator: In
      #              values:
      #                - "yes"
      containers:
        - name: mongo
          image: mongo:6.0
          command:
            - mongod
            - "--replSet"
            - rs0
            - "--bind_ip_all"
          ports:
            - containerPort: 27017
          volumeMounts:
            - name: data
              mountPath: /data/db
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: registry-pvc-$i
EOF

  # Create Service for each pod to expose DNS endpoint
  cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: Service
metadata:
  name: registry-$i
  namespace: $NAMESPACE
spec:
  selector:
    app: registry-$i
  ports:
    - port: 27017
      targetPort: 27017
EOF

done

# Step 2: ConfigMap to initialize the replica set
cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: registry-init
  namespace: $NAMESPACE
data:
  init.js: |
    rs.initiate({
      _id: "rs0",
      members: [
$(for i in $(seq 0 $((REPLICAS - 1))); do
echo "        { _id: $i, host: \"registry-$i.$NAMESPACE.svc.cluster.local:27017\" }$( [[ $i -lt $((REPLICAS - 1)) ]] && echo "," )"
done)
      ]
    });
EOF

# Step 3: Init client pod
cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: registry-init-client
  namespace: $NAMESPACE
spec:
  restartPolicy: Never
  containers:
    - name: mongo
      image: mongo:5.0
      command:
        - sh
        - -c
        - |
          echo "Waiting for registry-0 to be reachable..."
          until mongo --host registry-0.$NAMESPACE.svc.cluster.local --eval "db.adminCommand('ping')" >/dev/null 2>&1; do
            echo "Waiting for Mongo to be ready..."
            sleep 5
          done

          echo "Checking if replica set is already initiated..."
          if ! mongo --host registry-0.$NAMESPACE.svc.cluster.local --quiet --eval "rs.status().ok" | grep 1 >/dev/null; then
            echo "Running rs.initiate()..."
            mongo --host registry-0.$NAMESPACE.svc.cluster.local /config/init.js
          else
            echo "Replica set already initialized. Skipping."
          fi
      volumeMounts:
        - name: init-script
          mountPath: /config
  volumes:
    - name: init-script
      configMap:
        name: registry-init
EOF

echo "Deployment complete. Use: kubectl --insecure-skip-tls-verify get pods -n $NAMESPACE"
