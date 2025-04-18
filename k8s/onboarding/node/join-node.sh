#!/bin/bash

set -e

# Help function
usage() {
  echo "Usage: $0 --node-id <node_id> --cluster-id <cluster_id> --api-url <url> --kubeadm-join-cmd <quoted join command>"
  exit 1
}

# Install dependencies
echo "[INFO] Installing required Python dependencies..."
pip3 install --quiet psutil requests

# Check if nvidia-smi exists (optional GPU check)
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "[WARN] 'nvidia-smi' not found. GPU info may be unavailable."
fi

# Check if kubeadm is available
if ! command -v kubeadm >/dev/null 2>&1; then
  echo "[ERROR] kubeadm not found. Please install Kubernetes kubeadm CLI."
  exit 1
fi

# Path to Python script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/join_node_to_cluster.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo "[ERROR] Python script 'join_node_to_cluster.py' not found in ${SCRIPT_DIR}"
  exit 1
fi

# Execute the Python script with forwarded args
python3 "$PYTHON_SCRIPT" "$@"
