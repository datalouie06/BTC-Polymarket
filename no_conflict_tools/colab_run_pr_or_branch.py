# Copy this whole file into ONE Colab cell and run.
import os
import sys
import subprocess
from pathlib import Path

# ---------------- CONFIG ----------------
REPO_URL = "https://github.com/<ORG>/<REPO>.git"  # required
REPO_DIR = "/content/BTC-Polymarket"

# Set ONE target:
PR_NUMBER = ""     # e.g. "123"
BRANCH = "work"    # used when PR_NUMBER is empty

START_DATE = "2024-01-01"
END_DATE = "2024-03-31"
OUT_PATH = "/content/drive/MyDrive/polymarket_btc_inefficiency/data/pm_btc_reference.parquet"
REPORT_PATH = "/content/drive/MyDrive/polymarket_btc_inefficiency/backtest_report.md"
# ----------------------------------------


def sh(cmd: str, check: bool = True) -> int:
    print(f"\n$ {cmd}")
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if p.stdout:
        print(p.stdout)
    if p.returncode != 0 and p.stderr:
        print(p.stderr)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {cmd}")
    return p.returncode


try:
    from google.colab import drive

    drive.mount("/content/drive", force_remount=False)
except Exception as e:
    print("Drive mount skipped:", repr(e))

repo = Path(REPO_DIR)
if not repo.exists():
    if not REPO_URL.strip():
        raise FileNotFoundError("REPO_URL is empty and REPO_DIR does not exist.")
    sh(f"git clone {REPO_URL} {REPO_DIR}")
else:
    sh(f"git -C {REPO_DIR} fetch --all --prune")

if PR_NUMBER:
    sh(f"git -C {REPO_DIR} fetch origin pull/{PR_NUMBER}/head:pr-{PR_NUMBER}")
    sh(f"git -C {REPO_DIR} checkout pr-{PR_NUMBER}")
else:
    sh(f"git -C {REPO_DIR} checkout {BRANCH}")
    sh(f"git -C {REPO_DIR} pull --ff-only origin {BRANCH}")

sh(f"python -m pip install -q -r {REPO_DIR}/requirements.txt")
os.chdir(REPO_DIR)
sys.path.insert(0, str(Path(REPO_DIR) / "src"))

sh("make test")
sh(
    "PYTHONPATH=src python -m polymarket_btc.cli build-data "
    f"--output {OUT_PATH} --start {START_DATE} --end {END_DATE}"
)
sh(
    "PYTHONPATH=src python -m polymarket_btc.cli backtest "
    f"--dataset {OUT_PATH} --report {REPORT_PATH}"
)

print("\nDONE")
print("Dataset:", OUT_PATH)
print("Report:", REPORT_PATH)
