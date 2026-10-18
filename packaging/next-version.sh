#!/usr/bin/env bash
# Prints the next release version: one patch number above the highest v1.0.N tag.
set -euo pipefail

last="$(git tag --list 'v1.0.*' | sed 's/^v1\.0\.//' | grep -E '^[0-9]+$' | sort -n | tail -n 1 || true)"
echo "1.0.$(( ${last:-0} + 1 ))"
