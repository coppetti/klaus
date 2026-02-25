#!/bin/bash
# Klaus - Setup Launcher
# ==================================
# This script launches the setup wizard from the scripts/ directory

cd "$(dirname "$0")"
exec bash scripts/setup.sh "$@"
