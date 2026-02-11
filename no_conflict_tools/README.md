# No-conflict workflow tools

This folder is intentionally self-contained so you can update workflow docs/scripts
without touching existing project files and causing avoidable merge conflicts.

## What to use

- `colab_run_pr_or_branch.py`: one-cell-safe logic you can paste into Colab.
- `open_clean_pr.sh`: local shell workflow to build a clean PR branch from `origin/main`.

## Colab usage

1. Open `colab_run_pr_or_branch.py`.
2. Copy/paste the full file into a Colab cell.
3. Set `REPO_URL` and either `PR_NUMBER` or `BRANCH`.
4. Run the cell.

## Local usage

```bash
bash no_conflict_tools/open_clean_pr.sh <new_branch_name> <commit_sha_1> [<commit_sha_2> ...]
```

Example:

```bash
bash no_conflict_tools/open_clean_pr.sh clean/pr-btc-fix 814d5cb
```
