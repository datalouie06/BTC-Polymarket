from __future__ import annotations

import json
from pathlib import Path

from .ingest import IngestConfig, load_polymarket_btc_markets, load_reference_proxy

REQUIRED_COLUMNS = [
    "market_id",
    "market_title",
    "end_time",
    "strike_or_condition",
    "side",
    "ts",
    "mid",
    "bid",
    "ask",
    "volume",
    "liquidity",
    "fees_estimate",
    "reference_prob",
]


def build_dataset(output_path: str, start: str = "2024-01-01", end: str = "2024-04-30") -> list[dict]:
    cfg = IngestConfig(start=start, end=end)
    rows = load_polymarket_btc_markets(cfg)
    ref = load_reference_proxy(cfg, rows)
    out_rows = []
    for r in rows:
        row = {k: r[k] for k in REQUIRED_COLUMNS if k in r}
        row["reference_prob"] = ref.get((r["market_id"], r["ts"]), r["mid"])
        out_rows.append(row)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # JSON-lines with parquet extension for deterministic offline environment
    with out.open("w") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")
    meta = {"created_by": "build_dataset", "start": start, "end": end, "rows": len(out_rows), "format": "jsonl_parquet_compat"}
    (out.parent / f"{out.stem}.metadata.json").write_text(json.dumps(meta, indent=2))
    return out_rows


def read_dataset(path: str) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows
