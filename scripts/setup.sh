#!/bin/bash
# Klaus Setup
# ================================================
# Called from root via: ./setup.sh

cd "$(dirname "$0")/.."

# Check python3
if ! command -v python3 &> /dev/null; then
    echo "✗ python3 not found. Please install Python 3.8+"
    exit 1
fi

python3 installer/install_cli.py "$@"
