#!/bin/sh
# Shared, content-fingerprinted scope; never edits the index or worktree.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/scope.py" "$@"
