# Colab: one-cell updater to run a PR/branch safely

Use this single Colab cell when you want to update code in-runtime and run the pipeline without fighting path/import issues.

```python
# === ONE-CELL: pull latest code (or PR), install deps, run tests + pipeline ===
import os, sys, subprocess, textwrap
from pathlib import Path

# ---------- CONFIG ----------
REPO_URL = "https://github.com/<ORG>/<REPO>.git"   # required
REPO_DIR = "/content/BTC-Polymarket"

# Choose ONE target:
PR_NUMBER = ""           # e.g. "123" to test PR #123
BRANCH = "work"          # used when PR_NUMBER is empty

# Pipeline params
START_DATE = "2024-01-01"
END_DATE = "2024-03-31"
OUT_PATH = "/content/drive/MyDrive/polymarket_btc_inefficiency/data/pm_btc_reference.parquet"
REPORT_PATH = "/content/drive/MyDrive/polymarket_btc_inefficiency/backtest_report.md"
# ----------------------------

def sh(cmd, check=True):
    print("\\n$", cmd)
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if p.stdout:
        print(p.stdout)
    if p.returncode != 0 and p.stderr:
        print(p.stderr)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {cmd}")
    return p.returncode

# 1) Mount drive (if in Colab)
try:
    from google.colab import drive
    drive.mount("/content/drive", force_remount=False)
except Exception as e:
    print("Drive mount skipped:", repr(e))

# 2) Clone/fetch repo
repo = Path(REPO_DIR)
if not repo.exists():
    if not REPO_URL.strip():
        raise FileNotFoundError("REPO_URL is empty and repo folder does not exist.")
    sh(f"git clone {REPO_URL} {REPO_DIR}")
else:
    sh(f"git -C {REPO_DIR} fetch --all --prune")

# 3) Checkout PR or branch
if PR_NUMBER:
    sh(f"git -C {REPO_DIR} fetch origin pull/{PR_NUMBER}/head:pr-{PR_NUMBER}")
    sh(f"git -C {REPO_DIR} checkout pr-{PR_NUMBER}")
else:
    sh(f"git -C {REPO_DIR} checkout {BRANCH}")
    sh(f"git -C {REPO_DIR} pull --ff-only origin {BRANCH}")

# 4) Install deps and expose src/
sh(f"python -m pip install -q -r {REPO_DIR}/requirements.txt")
os.chdir(REPO_DIR)
sys.path.insert(0, str(Path(REPO_DIR) / "src"))

# 5) Run quality gates first
sh("make test")

# 6) Build data + run backtest
sh(f"PYTHONPATH=src python -m polymarket_btc.cli build-data --output {OUT_PATH} --start {START_DATE} --end {END_DATE}")
sh(f"PYTHONPATH=src python -m polymarket_btc.cli backtest --dataset {OUT_PATH} --report {REPORT_PATH}")

print("\\nDONE")
print("Dataset:", OUT_PATH)
print("Report:", REPORT_PATH)
```

## Notes
- Set `PR_NUMBER` to run a PR head directly; leave it blank to follow `BRANCH`.
- If tests fail, stop and fix code before trusting results.
- If you see `ModuleNotFoundError: polymarket_btc`, confirm `sys.path` includes `<repo>/src`.
