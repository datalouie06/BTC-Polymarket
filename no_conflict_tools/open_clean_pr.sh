#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <new_branch_name> <commit_sha_1> [<commit_sha_2> ...]"
  exit 1
fi

NEW_BRANCH="$1"
shift
COMMITS=("$@")


echo "[1/6] Fetching origin..."
git fetch origin

echo "[2/6] Creating clean branch from origin/main: ${NEW_BRANCH}"
git checkout -b "${NEW_BRANCH}" origin/main

echo "[3/6] Cherry-picking commits: ${COMMITS[*]}"
git cherry-pick "${COMMITS[@]}"

echo "[4/6] Running tests..."
make test

echo "[5/6] Running data build + backtest..."
make build_data
make backtest

echo "[6/6] Pushing branch..."
git push -u origin "${NEW_BRANCH}"

echo "Done. Open a PR from ${NEW_BRANCH} -> main"
