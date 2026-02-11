from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import math
import random


@dataclass
class BacktestConfig:
    entry_threshold: float = 0.05
    exit_threshold: float = 0.01
    max_position: float = 1.0
    cost_bps: float = 35
    slippage_bps: float = 15
    latency_steps: int = 1
    walk_forward_splits: int = 3


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def prepare_features(rows: list[dict]) -> list[dict]:
    out = []
    for r in sorted(rows, key=lambda x: (x["market_id"], x["side"], x["ts"])):
        row = dict(r)
        row["polymarket_prob"] = min(0.999, max(0.001, float(r["mid"])))
        row["edge"] = float(r["reference_prob"]) - row["polymarket_prob"]
        row["spread"] = max(0.0, float(r["ask"]) - float(r["bid"]))
        out.append(row)
    return out


def simulate_backtest(rows: list[dict], cfg: BacktestConfig | None = None):
    cfg = cfg or BacktestConfig()
    feats = prepare_features(rows)
    grouped: dict[tuple[str, str], list[dict]] = {}
    for r in feats:
        grouped.setdefault((r["market_id"], r["side"]), []).append(r)

    bt: list[dict] = []
    for _, grp in grouped.items():
        grp = sorted(grp, key=lambda x: x["ts"])
        signals = []
        for r in grp:
            e = r["edge"]
            if e > cfg.entry_threshold:
                signals.append(1.0)
            elif e < -cfg.entry_threshold:
                signals.append(-1.0)
            else:
                signals.append(0.0)
        position = []
        cur = 0.0
        for i, s in enumerate(signals):
            if s != 0.0:
                cur = s
            if abs(grp[i]["edge"]) < cfg.exit_threshold:
                cur = 0.0
            cur = max(-cfg.max_position, min(cfg.max_position, cur))
            position.append(cur)
        lagged = [0.0] * len(position)
        for i, p in enumerate(position):
            j = i + cfg.latency_steps
            if j < len(lagged):
                lagged[j] = p

        for i, r in enumerate(grp):
            prev_mid = float(grp[i - 1]["mid"]) if i > 0 else float(r["mid"])
            ret = 0.0 if prev_mid == 0 else (float(r["mid"]) - prev_mid) / prev_mid
            prev_pos = lagged[i - 1] if i > 0 else 0.0
            trade_size = abs(lagged[i] - prev_pos)
            costs = trade_size * ((cfg.cost_bps + cfg.slippage_bps) / 10000.0 + r["spread"])
            pnl = lagged[i] * ret - costs
            row = dict(r)
            row.update({"signal": signals[i], "position": lagged[i], "ret": ret, "trade_size": trade_size, "costs": costs, "pnl": pnl})
            bt.append(row)

    bt = sorted(bt, key=lambda x: (x["market_id"], x["side"], x["ts"]))
    metrics = compute_metrics(bt)
    metrics.update(robustness_checks(bt, cfg))
    return bt, metrics


def compute_metrics(bt: list[dict]) -> dict[str, float]:
    pnl = [r["pnl"] for r in bt]
    eq = []
    cur = 1.0
    for p in pnl:
        cur *= 1 + p
        eq.append(cur)
    mean = sum(pnl) / len(pnl) if pnl else 0.0
    var = sum((x - mean) ** 2 for x in pnl) / max(len(pnl), 1)
    std = math.sqrt(var)
    sharpe = math.sqrt(365 * 6) * mean / (std + 1e-12)
    if bt:
        years = max((_dt(bt[-1]["ts"]) - _dt(bt[0]["ts"])).total_seconds() / (365 * 86400), 1 / 365)
        cagr = eq[-1] ** (1 / years) - 1
    else:
        cagr = 0.0
    peak = 1.0
    max_dd = 0.0
    for v in eq:
        peak = max(peak, v)
        dd = v / peak - 1
        max_dd = min(max_dd, dd)
    hit_rate = sum(1 for x in pnl if x > 0) / len(pnl) if pnl else 0.0
    trades = [r["pnl"] for r in bt if r["trade_size"] > 0]
    avg_trade = sum(trades) / len(trades) if trades else 0.0
    exposure = sum(abs(r["position"]) for r in bt) / len(bt) if bt else 0.0
    turnover = sum(r["trade_size"] for r in bt)
    return {"sharpe": sharpe, "cagr": cagr, "max_dd": max_dd, "hit_rate": hit_rate, "avg_trade_return": avg_trade, "exposure": exposure, "turnover": turnover}


def robustness_checks(bt: list[dict], cfg: BacktestConfig) -> dict[str, float]:
    out = {}
    if not bt:
        return {"oos_sharpe": 0.0, "walk_forward_mean_pnl": 0.0, "placebo_mean_pnl": 0.0, "cost_sensitivity_pnl": 0.0, "latency2_mean_pnl": 0.0}
    n = len(bt)
    oos = [r["pnl"] for r in bt[int(0.7 * n) :]]
    m = sum(oos) / len(oos)
    s = math.sqrt(sum((x - m) ** 2 for x in oos) / max(len(oos), 1))
    out["oos_sharpe"] = math.sqrt(365 * 6) * m / (s + 1e-12)

    split = max(n // max(cfg.walk_forward_splits, 1), 1)
    vals = []
    edges = [abs(r["edge"]) for r in bt]
    for i in range(split, n, split):
        tr = sorted(edges[:i])
        q = tr[int(0.7 * (len(tr) - 1))] if tr else 0.0
        test = [bt[j]["pnl"] for j in range(i, min(i + split, n)) if abs(bt[j]["edge"]) > q]
        if test:
            vals.append(sum(test) / len(test))
    out["walk_forward_mean_pnl"] = sum(vals) / len(vals) if vals else 0.0

    rng = random.Random(42)
    by_day: dict[str, list[dict]] = {}
    for r in bt:
        day = r["ts"][:10]
        by_day.setdefault(day, []).append(r)
    placebo = []
    for day, rows in by_day.items():
        sigs = [r["signal"] for r in rows]
        rng.shuffle(sigs)
        for i, r in enumerate(rows):
            placebo.append(sigs[i] * r["ret"])
    out["placebo_mean_pnl"] = sum(placebo) / len(placebo) if placebo else 0.0
    out["cost_sensitivity_pnl"] = sum(r["pnl"] - r["trade_size"] * 0.002 for r in bt) / len(bt)
    out["latency2_mean_pnl"] = sum(((bt[i - 2]["position"] if i >= 2 else 0.0) * bt[i]["ret"] - bt[i]["costs"]) for i in range(len(bt))) / len(bt)
    return out


def write_report(metrics: dict[str, float], path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Backtest Summary", "", "| Metric | Value |", "|---|---:|"]
    for k, v in metrics.items():
        lines.append(f"| {k} | {v:.6f} |")
    verdict = "yes" if metrics.get("sharpe", 0) > 0.5 and metrics.get("oos_sharpe", 0) > 0 else "unclear"
    lines += ["", f"Final verdict on inefficiency evidence: **{verdict}**"]
    p.write_text("\n".join(lines))
