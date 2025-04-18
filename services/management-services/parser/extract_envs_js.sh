#!/bin/bash

# Ensure a directory is provided as an argument
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_directory>"
    exit 1
fi

# Directory containing JavaScript/TypeScript files
dir="$1"

# Find all JS/TS files in the directory, excluding node_modules, and extract environment variables
find "$dir" -type d -name "node_modules" -prune -o \
    -type f \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" \) -print | while read -r file; do
    grep -oP "process\.env\.\K[^\s\);]+" "$file" 2>/dev/null
done | sort | uniq

