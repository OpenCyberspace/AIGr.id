#!/bin/bash

# Usage:
# ./push-images.sh <prefix>

PREFIX="$1"

if [[ -z "$PREFIX" ]]; then
    echo "❌ Usage: $0 <prefix>"
    echo "Example: $0 34.58.1.86:31280"
    exit 1
fi

echo "🔍 Searching for images starting with: $PREFIX"

# List images with the given prefix
docker images --format "{{.Repository}}:{{.Tag}}" | grep "^$PREFIX" | while read -r image; do
    echo "📤 Pushing $image"
    docker push "$image"

    if [[ $? -eq 0 ]]; then
        echo "✅ Successfully pushed $image"
    else
        echo "❌ Failed to push $image"
    fi
done

echo "✅ Push process complete."
