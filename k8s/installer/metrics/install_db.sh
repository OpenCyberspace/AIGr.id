#!/bin/bash

# USAGE: ./deploy_metrics_db.sh <replica-count> [storage-size]
REPLICAS=$1
STORAGE=${2:-1Gi}
NAMESPACE="metrics-system"

if [[ -z "$REPLICAS" ]]; then
  echo "Usage: $0 <replica-count> [storage-size]"
  exit 1
fi

echo "🚀 Deploying $REPLICAS MongoDB metrics replica nodes with $STORAGE storage each in namespace '$NAMESPACE'..."

kubectl --insecure-skip-tls-verify create namespace $NAMESPACE --dry-run=client -o yaml | kubectl --insecure-skip-tls-verify apply -f -

for i in $(seq 0 $((REPLICAS - 1))); do
  echo "🔧 Setting up metrics-db-$i..."

  cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: metrics-db-pv-$i
  labels:
    volume-id: metrics-db-$i
spec:
  capacity:
    storage: $STORAGE
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  hostPath:
    path: /mnt/data/metrics-db-$i
  persistentVolumeReclaimPolicy: Retain
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: metrics-db
              operator: In
              values:
                - "yes"
EOF

  cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: metrics-db-pvc-$i
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  volumeName: metrics-db-pv-$i
  resources:
    requests:
      storage: $STORAGE
EOF

  cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-db-$i
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: metrics-db-$i
  template:
    metadata:
      labels:
        app: metrics-db-$i
    spec:
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
            claimName: metrics-db-pvc-$i
EOF

  cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: Service
metadata:
  name: metrics-db-$i
  namespace: $NAMESPACE
spec:
  selector:
    app: metrics-db-$i
  ports:
    - port: 27017
      targetPort: 27017
EOF

done

cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: metrics-db-init
  namespace: $NAMESPACE
data:
  init.js: |
    rs.initiate({
      _id: "rs0",
      members: [
$(for i in $(seq 0 $((REPLICAS - 1))); do
echo "        { _id: $i, host: \"metrics-db-$i.$NAMESPACE.svc.cluster.local:27017\" }$( [[ $i -lt $((REPLICAS - 1)) ]] && echo "," )"
done)
      ]
    });
EOF

cat <<EOF | kubectl --insecure-skip-tls-verify apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: metrics-db-init-client
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
          echo "Waiting for metrics-db-0 to be reachable..."
          until mongo --host metrics-db-0.$NAMESPACE.svc.cluster.local --eval "db.adminCommand('ping')" >/dev/null 2>&1; do
            echo "Waiting for Mongo to be ready..."
            sleep 5
          done

          echo "Checking if replica set is already initiated..."
          if ! mongo --host metrics-db-0.$NAMESPACE.svc.cluster.local --quiet --eval "rs.status().ok" | grep 1 >/dev/null; then
            echo "Running rs.initiate()..."
            mongo --host metrics-db-0.$NAMESPACE.svc.cluster.local /config/init.js
          else
            echo "Replica set already initialized. Skipping."
          fi
      volumeMounts:
        - name: init-script
          mountPath: /config
  volumes:
    - name: init-script
      configMap:
        name: metrics-db-init
EOF

echo "✅ Metrics DB deployment complete. Run: kubectl --insecure-skip-tls-verify get pods -n $NAMESPACE"
