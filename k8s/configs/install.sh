#!/bin/bash

# File: deploy.sh

CONFIG_FILE="config_gpu.toml"
REMOTE_PATH="/etc/containerd/config.toml"
SSH_USER="prasanna"  # Change if needed

# ✅ Hardcoded list of IPs
IP_LIST=(
    34.45.74.204
    34.9.182.18
)

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Error: $CONFIG_FILE not found in current directory."
    exit 1
fi

for ip in "${IP_LIST[@]}"; do
    echo ">>> Deploying to $ip"
    
    scp "$CONFIG_FILE" "$SSH_USER@$ip:/tmp/config.toml"
    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to copy config to $ip"
        continue
    fi

    ssh "$SSH_USER@$ip" "sudo mv /tmp/config.toml $REMOTE_PATH && sudo systemctl restart containerd"
    if [[ $? -eq 0 ]]; then
        echo "✅ Successfully updated containerd config on $ip"
    else
        echo "❌ Failed to update containerd config on $ip"
    fi
done
