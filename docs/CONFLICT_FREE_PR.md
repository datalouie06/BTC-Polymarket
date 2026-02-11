# Conflict-safe PR workflow (new branch from latest main)

If your current PR branch is tangled, do this instead:

1. Start a clean branch from the latest target branch (usually `main`).
2. Bring over only the commits you actually want (`cherry-pick`).
3. Run tests/build/backtest.
4. Push the clean branch and open a PR from it.

## Commands

```bash
# 0) Save any local edits first
git status

# 1) Fetch latest refs
git fetch origin

# 2) Create a clean branch from target branch
git checkout -b clean/pr-btc-inefficiency origin/main

# 3) Bring over your good commits (one or more)
# Replace with your real commit hashes from old branch
git cherry-pick <commit_sha_1> <commit_sha_2>

# 4) Resolve conflicts if any, then continue
# (Only needed when cherry-pick pauses)
git add <resolved_files>
git cherry-pick --continue

# 5) Validate
make test
make build_data
make backtest

# 6) Push clean branch and open PR
git push -u origin clean/pr-btc-inefficiency
```

## Practical tips to minimize conflicts

- Avoid cherry-picking generated artifacts unless required (`*.parquet`, generated reports).
- Prefer regenerating outputs on the new branch (`make build_data`, `make backtest`).
- Keep PR scope small: code + docs, not large data artifacts unless explicitly needed.

## If you want to keep only your final current commit

```bash
git fetch origin
git checkout -b clean/pr-btc-inefficiency origin/main
git cherry-pick <latest_good_commit>
make test
make build_data
make backtest
git push -u origin clean/pr-btc-inefficiency
```
