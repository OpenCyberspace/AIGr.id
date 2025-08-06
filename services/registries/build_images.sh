#!/bin/bash

# Registry prefix
REGISTRY="164.52.207.172:32633/registries"

# Loop through each folder in current directory
for dir in */ ; do
    # Remove trailing slash
    folder_name="${dir%/}"
    dockerfile_path="$folder_name/Dockerfile"

    if [[ -f "$dockerfile_path" ]]; then
        image_name="$REGISTRY/$folder_name"
        echo "🛠️ Building image for $folder_name..."
        docker build -t "$image_name" "$folder_name"

        if [[ $? -eq 0 ]]; then
            echo "📦 Pushing $image_name to registry..."
            docker push "$image_name"
        else
            echo "❌ Build failed for $folder_name. Skipping push."
        fi
    else
        echo "⚠️ Dockerfile not found in $folder_name. Skipping..."
    fi
done
