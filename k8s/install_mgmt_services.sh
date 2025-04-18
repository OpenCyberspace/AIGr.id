#!/bin/bash

set -e

# === CONFIGURABLE ===
REGISTRY_REPLICAS=3
REGISTRY_SIZE="10Gi"
METRICS_REPLICAS=3
METRICS_SIZE="10Gi"

read -p "Enter registry node name (for DB): " REGISTRY_NODE
read -p "Enter metrics node name (for Metrics DB): " METRICS_NODE

echo ""
echo "=== Starting Management Cluster Setup ==="
echo ""


# === STEP 1: Install Registry DB ===
read -p "[1/5] Deploy Registry DB? (yes/no): " step2
if [[ "$step2" == "yes" ]]; then
  echo "Deploying Registry DB..."
  cd k8s/
  ./installer/db/install.sh "$REGISTRY_REPLICAS" "$REGISTRY_SIZE"
  echo "✔ Registry DB deployed."
  sleep 15
else
  echo "⏩ Skipping registry DB installation."
fi

# === STEP 2: Deploy Registry Services ===
read -p "[2/5] Deploy Registry Services? (yes/no): " step3
if [[ "$step3" == "yes" ]]; then
  echo "Deploying Registry Services..."
  chmod +x ./installer/registries/install.sh
  ./installer/registries/install.sh
  echo "✔ Registry Services deployed."
  sleep 10
else
  echo "⏩ Skipping registry services."
fi

# === STEP 3: Deploy Utility Services ===
read -p "[3/5] Deploy Utility Services? (yes/no): " step4
if [[ "$step4" == "yes" ]]; then
  echo "Deploying Utility Services..."
  chmod +x ./installer/utils/install.sh
  ./installer/utils/install.sh
  echo "✔ Utility Services deployed."
  sleep 10
else
  echo "⏩ Skipping utility services."
fi

# === STEP 4: Deploy Utility Services ===
read -p "[4/5] Deploy Metrics DB and Services? (yes/no): " step5
if [[ "$step5" == "yes" ]]; then
  echo "Deploying Metrics DB..."
  ./installer/metrics/install_db.sh "$METRICS_REPLICAS" "$METRICS_SIZE"
  sleep 15

  echo "Deploying Metrics Services..."
  cd installer/metrics
  chmod +x install.sh
  ./install.sh
  cd ../../
  echo "✔ Metrics System deployed."
  sleep 10
else
  echo "⏩ Skipping metrics system."
fi

# === STEP 5: Deploy Core Services ===
read -p "[5/5] Deploy Core Services (parser, controller)? (yes/no): " step6
if [[ "$step6" == "yes" ]]; then
  echo "Deploying Core Services..."
  cd installer/services
  chmod +x install.sh
  ./install.sh
  cd ../../
  echo "✔ Core Services deployed."
else
  echo "⏩ Skipping core services."
fi

echo ""
echo "✅ Management cluster setup complete (selected phases)."
