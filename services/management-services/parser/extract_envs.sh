#!/bin/bash

# Ensure a directory is provided as an argument
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_directory>"
    exit 1
fi

# Directory containing Python files
dir="$1"

# Find all Python files in the directory and its subdirectories, then extract environment variables
find "$dir" -type f -name "*.py" | while read -r file; do
    grep -oP "os.getenv\([\"']\K[^\"']+" "$file" 2>/dev/null
done | sort | uniq
