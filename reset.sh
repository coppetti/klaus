#!/bin/bash
# Klaus - Reset Launcher
# ==================================
# This script launches the reset script from the scripts/ directory

cd "$(dirname "$0")"
exec bash scripts/reset.sh "$@"
