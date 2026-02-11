from __future__ import annotations

import argparse
import json

from .backtest import BacktestConfig, simulate_backtest, write_report
from .dataset import build_dataset, read_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket BTC research pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build-data")
    b.add_argument("--output", required=True)
    b.add_argument("--start", default="2024-01-01")
    b.add_argument("--end", default="2024-04-30")

    t = sub.add_parser("backtest")
    t.add_argument("--dataset", required=True)
    t.add_argument("--report", default="docs/BACKTEST_SUMMARY.md")
    t.add_argument("--entry-threshold", type=float, default=0.05)
    t.add_argument("--exit-threshold", type=float, default=0.01)

    args = parser.parse_args()

    if args.cmd == "build-data":
        df = build_dataset(args.output, start=args.start, end=args.end)
        print(json.dumps({"rows": len(df), "output": args.output}, indent=2))
    elif args.cmd == "backtest":
        df = read_dataset(args.dataset)
        cfg = BacktestConfig(entry_threshold=args.entry_threshold, exit_threshold=args.exit_threshold)
        _, metrics = simulate_backtest(df, cfg)
        write_report(metrics, args.report)
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
