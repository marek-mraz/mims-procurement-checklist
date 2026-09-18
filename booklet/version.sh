#!/bin/sh
# Prints the booklet's edition number.
#   booklet/VERSION holds the base: the MIMs Plus release the booklet follows (9.0).
#   The third number counts published editions: git tags v9.0.1, v9.0.2, …
#   RELEASE=1 (the main branch in CI)  -> the next edition number, 9.0.2
#   otherwise (your machine, dev, PRs) -> the same number marked as a draft, 9.0.2-dev
# The tag is created by the GitHub workflow after a successful build on main.
cd "$(dirname "$0")"
base=$(cat VERSION)
last=$(git tag -l "v$base.*" 2>/dev/null | sed "s/^v$base\.//" | grep -E '^[0-9]+$' | sort -n | tail -1)
next="$base.$(( ${last:-0} + 1 ))"
if [ "$RELEASE" = 1 ]; then echo "$next"; else echo "$next-dev"; fi
