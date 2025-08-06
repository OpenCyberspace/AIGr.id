#!/bin/bash

# Usage:
# ./retag-images.sh <old_prefix> <new_prefix>

OLD_PREFIX="$1"
NEW_PREFIX="$2"

if [[ -z "$OLD_PREFIX" || -z "$NEW_PREFIX" ]]; then
    echo "❌ Usage: $0 <old_prefix> <new_prefix>"
    exit 1
fi

echo "🔍 Searching for images starting with: $OLD_PREFIX"

# List images and filter those with the old prefix
docker images --format "{{.Repository}}:{{.Tag}}" | grep "^$OLD_PREFIX" | while read -r image; do
    # Strip the old prefix
    suffix="${image#$OLD_PREFIX}"
    
    # Create new image name
    new_image="$NEW_PREFIX$suffix"

    echo "🔄 Tagging $image -> $new_image"
    docker tag "$image" "$new_image"
done

echo "✅ Tagging complete."
