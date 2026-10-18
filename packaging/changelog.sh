#!/usr/bin/env bash
# Prints release notes for a git range: one bullet per commit subject,
# with any "- " or "* " lines from the commit body nested underneath.
set -euo pipefail

range="${1:-HEAD}"
for commit in $(git log --no-merges --format=%H "$range"); do
    echo "- $(git log -1 --format='%s (%h)' "$commit")"
    while IFS= read -r line; do
        case "$line" in
            "- "* | "* "*) echo "  - ${line:2}" ;;
        esac
    done < <(git log -1 --format=%b "$commit")
done
