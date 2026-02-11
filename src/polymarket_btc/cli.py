from __future__ import annotations

import argparse
import json

from .backtest import BacktestConfig, simulate_backtest, write_report
from .dataset import build_dataset, read_dataset


def _pretty(metrics: dict[str, float]) -> str:
    keys = [
        "scans",
        "bets",
        "bet_rate",
        "mean_roi_per_bet",
        "median_roi_per_bet",
        "win_rate",
        "full_loss_rate",
        "mean_expected_edge",
        "mean_roi_per_scan",
        "pnl_sharpe",
        "oos_pnl_sharpe",
        "pnl_max_drawdown",
        "exposure",
        "turnover",
    ]
    lines = ["Backtest metrics:"]
    for k in keys:
        if k in metrics:
            lines.append(f"  - {k:22s}: {metrics[k]:.6f}")
    return "\n".join(lines)


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
    t.add_argument("--min-price", type=float, default=0.05)
    t.add_argument("--max-price", type=float, default=0.95)
    t.add_argument("--min-volume", type=float, default=0.0)

    args = parser.parse_args()

    if args.cmd == "build-data":
        rows = build_dataset(args.output, start=args.start, end=args.end)
        print(json.dumps({"rows": len(rows), "output": args.output}, indent=2))
    elif args.cmd == "backtest":
        rows = read_dataset(args.dataset)
        cfg = BacktestConfig(
            entry_threshold=args.entry_threshold,
            exit_threshold=args.exit_threshold,
            min_price=args.min_price,
            max_price=args.max_price,
            min_volume=args.min_volume,
        )
        _, metrics, bets = simulate_backtest(rows, cfg)
        write_report(metrics, bets, args.report)
        print(_pretty(metrics))


if __name__ == "__main__":
    main()
