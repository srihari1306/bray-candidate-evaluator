#!/usr/bin/env bash
set -e

# Get directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure output directory exists
mkdir -p ../teams-panel-dist

# Navigate to the manifest directory
cd public/manifest

# Create the zip file containing only the target manifest assets
zip ../../../teams-panel-dist/smart-interviewer.zip manifest.json color.png outline.png

echo 'Upload teams-panel-dist/smart-interviewer.zip to Teams Admin Center'
