#!/bin/sh
# Discover specs/rules with the same scope and symlink boundary as review.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/../../review/scripts/refs.py" "$@"
