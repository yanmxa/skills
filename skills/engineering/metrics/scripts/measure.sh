#!/bin/sh
# Inventory by default; --run-tools / --project-checks require explicit approval.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/../../review/scripts/measure.py" "$@"
