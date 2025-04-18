#!/bin/bash

# ./install_db.sh <storage-size> <replica-count> <db-name> <username> <password>

STORAGE=${1:-2Gi}
REPLICAS=${2:-1}
DB_NAME=${3:-mydb}
DB_USER=${4:-myuser}
DB_PASSWORD=${5:-mypassword}
NAMESPACE="inference-server"

echo "Deploying TimescaleDB with:"
echo "- Storage size: $STORAGE"
echo "- Replicas: $REPLICAS"
echo "- DB name: $DB_NAME"
echo "- Username: $DB_USER"
echo "- Namespace: $NAMESPACE"

# Step 1: Create Namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Step 2: Create PVC for primary
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: timescaledb-primary-pvc
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: $STORAGE
EOF

# Step 3: Deploy Primary
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: timescaledb-primary
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      role: primary
      app: timescaledb
  template:
    metadata:
      labels:
        role: primary
        app: timescaledb
    spec:
      containers:
        - name: timescaledb
          image: timescale/timescaledb-ha:pg15-latest
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: $DB_NAME
            - name: POSTGRES_USER
              value: $DB_USER
            - name: POSTGRES_PASSWORD
              value: $DB_PASSWORD
            - name: TIMESCALEDB_TELEMETRY
              value: "off"
            - name: PG_MODE
              value: "primary"
            - name: PG_PRIMARY_USER
              value: $DB_USER
            - name: PG_PRIMARY_PASSWORD
              value: $DB_PASSWORD
          volumeMounts:
            - mountPath: /var/lib/postgresql/data
              name: data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: timescaledb-primary-pvc
EOF

# Step 4: Expose Primary as a Service
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: timescaledb-primary
  namespace: $NAMESPACE
spec:
  selector:
    role: primary
    app: timescaledb
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
  clusterIP: None
EOF

# Step 5: Create replicas
for i in $(seq 1 $REPLICAS); do
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: timescaledb-replica-$i-pvc
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: $STORAGE
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: timescaledb-replica-$i
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      role: replica-$i
      app: timescaledb
  template:
    metadata:
      labels:
        role: replica-$i
        app: timescaledb
    spec:
      containers:
        - name: timescaledb
          image: timescale/timescaledb-ha:pg15-latest
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: $DB_NAME
            - name: POSTGRES_USER
              value: $DB_USER
            - name: POSTGRES_PASSWORD
              value: $DB_PASSWORD
            - name: PG_MODE
              value: "replica"
            - name: PG_PRIMARY_HOST
              value: timescaledb-primary.$NAMESPACE.svc.cluster.local
            - name: PG_PRIMARY_PORT
              value: "5432"
            - name: PG_PRIMARY_USER
              value: $DB_USER
            - name: PG_PRIMARY_PASSWORD
              value: $DB_PASSWORD
          volumeMounts:
            - mountPath: /var/lib/postgresql/data
              name: data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: timescaledb-replica-$i-pvc
EOF
done

echo "TimescaleDB standalone deployment with $REPLICAS replica(s) completed."
