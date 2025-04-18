#!/bin/bash

# USAGE: ./deploy_assets_db.sh <replica-count> [storage-size]
REPLICAS=$1
STORAGE=${2:-1Gi}
NAMESPACE="assets-db"

if [[ -z "$REPLICAS" ]]; then
  echo "Usage: $0 <replica-count> [storage-size]"
  exit 1
fi

echo "Deploying $REPLICAS MongoDB assets-db replica nodes with $STORAGE storage each in namespace '$NAMESPACE'..."

kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

for i in $(seq 0 $((REPLICAS - 1))); do
  echo "🔧 Setting up assets-db-$i..."

  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: assets-db-pv-$i
  labels:
    volume-id: assets-db-$i
spec:
  capacity:
    storage: $STORAGE
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  hostPath:
    path: /mnt/data/assets-db-$i
  persistentVolumeReclaimPolicy: Retain
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: assets-db
              operator: In
              values:
                - "yes"
EOF

  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: assets-db-pvc-$i
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  volumeName: assets-db-pv-$i
  resources:
    requests:
      storage: $STORAGE
EOF

  cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: assets-db-$i
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: assets-db-$i
  template:
    metadata:
      labels:
        app: assets-db-$i
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
            claimName: assets-db-pvc-$i
EOF

  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: assets-db-$i
  namespace: $NAMESPACE
spec:
  selector:
    app: assets-db-$i
  ports:
    - port: 27017
      targetPort: 27017
EOF

done

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: assets-db-init
  namespace: $NAMESPACE
data:
  init.js: |
    rs.initiate({
      _id: "rs0",
      members: [
$(for i in $(seq 0 $((REPLICAS - 1))); do
echo "        { _id: $i, host: \"assets-db-$i.$NAMESPACE.svc.cluster.local:27017\" }$( [[ $i -lt $((REPLICAS - 1)) ]] && echo "," )"
done)
      ]
    });
EOF

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: assets-db-init-client
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
          echo "Waiting for assets-db-0 to be reachable..."
          until mongo --host assets-db-0.$NAMESPACE.svc.cluster.local --eval "db.adminCommand('ping')" >/dev/null 2>&1; do
            echo "Waiting for Mongo to be ready..."
            sleep 5
          done

          echo "Checking if replica set is already initiated..."
          if ! mongo --host assets-db-0.$NAMESPACE.svc.cluster.local --quiet --eval "rs.status().ok" | grep 1 >/dev/null; then
            echo "Running rs.initiate()..."
            mongo --host assets-db-0.$NAMESPACE.svc.cluster.local /config/init.js
          else
            echo "Replica set already initialized. Skipping."
          fi
      volumeMounts:
        - name: init-script
          mountPath: /config
  volumes:
    - name: init-script
      configMap:
        name: assets-db-init
EOF

echo "Assets DB deployment complete. Run: kubectl get pods -n $NAMESPACE"
