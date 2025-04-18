#!/bin/bash

set -e

# Function to print usage
usage() {
  echo "Usage: $0 <cluster_json_file> [--onboard --api-url <url>]"
  exit 1
}

# Ensure Python is installed
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is not installed."
  exit 1
fi

# Step 1: Install dependencies
echo "[INFO] Installing required Python dependencies..."
pip3 install --quiet kubernetes requests

# Step 2: Check if ~/.kube/config exists
if [ ! -f "$HOME/.kube/config" ]; then
  echo "Error: Kubernetes config not found at ~/.kube/config"
  exit 1
fi

# Step 3: Pass all arguments to the Python script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/populate_cluster_info.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo "Error: populate_cluster_info.py not found in script directory."
  exit 1
fi

echo "[INFO] Running populate_cluster_info.py..."
python3 "$PYTHON_SCRIPT" "$@"
