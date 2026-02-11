from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import math
import random
from statistics import mean, median


@dataclass
class BacktestConfig:
    entry_threshold: float = 0.05
    exit_threshold: float = 0.01
    max_position: float = 1.0
    cost_bps: float = 35
    slippage_bps: float = 15
    latency_steps: int = 1
    walk_forward_splits: int = 3
    min_price: float = 0.05
    max_price: float = 0.95
    min_volume: float = 0.0


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def prepare_features(rows: list[dict]) -> list[dict]:
    out = []
    for r in sorted(rows, key=lambda x: (x["market_id"], x["side"], x["ts"])):
        row = dict(r)
        row["polymarket_prob"] = min(0.999, max(0.001, float(r["mid"])))
        row["edge"] = float(r["reference_prob"]) - row["polymarket_prob"]
        row["spread"] = max(0.0, float(r["ask"]) - float(r["bid"]))
        row["market_type"] = str(r.get("strike_or_condition", "unknown")).split(":")[0]
        out.append(row)
    return out


def _terminal_yes_prob(rows: list[dict]) -> dict[str, float]:
    terms = {}
    yes_rows: dict[str, list[dict]] = {}
    for r in rows:
        if r["side"] == "yes":
            yes_rows.setdefault(r["market_id"], []).append(r)
    for mid, grp in yes_rows.items():
        last = sorted(grp, key=lambda x: x["ts"])[-1]
        terms[mid] = float(last["mid"])
    return terms


def pick_best_bets(rows: list[dict], cfg: BacktestConfig) -> list[dict]:
    feats = prepare_features(rows)
    terminal = _terminal_yes_prob(feats)

    filtered = []
    for r in feats:
        if abs(r["edge"]) < cfg.entry_threshold:
            continue
        if not (cfg.min_price <= float(r["mid"]) <= cfg.max_price):
            continue
        if float(r.get("volume", 0.0)) < cfg.min_volume:
            continue
        filtered.append(r)

    by_scan: dict[str, list[dict]] = {}
    for r in filtered:
        by_scan.setdefault(r["ts"], []).append(r)

    picked: list[dict] = []
    for ts, candidates in by_scan.items():
        candidates = sorted(candidates, key=lambda x: (abs(x["edge"]), -float(x["volume"])), reverse=True)
        bet = dict(candidates[0])
        yes_final = terminal.get(bet["market_id"], 0.5)
        if bet["side"] == "yes":
            payoff_prob = yes_final
        else:
            payoff_prob = 1 - yes_final
        entry_price = float(bet["ask"])  # pessimistic fill
        raw_roi = _safe_div(payoff_prob - entry_price, max(entry_price, 1e-6))
        cost = (cfg.cost_bps + cfg.slippage_bps) / 10000.0
        bet["expected_edge"] = float(bet["edge"])
        bet["payoff_prob_proxy"] = payoff_prob
        bet["roi_real"] = raw_roi - cost
        bet["bet_side"] = "buy_yes" if bet["side"] == "yes" else "buy_no"
        picked.append(bet)
    return sorted(picked, key=lambda x: x["ts"])


def summarize_bets(bets: list[dict], total_scans: int) -> dict[str, float]:
    if not bets:
        return {
            "scans": float(total_scans),
            "bets": 0.0,
            "bet_rate": 0.0,
            "mean_roi_per_bet": 0.0,
            "median_roi_per_bet": 0.0,
            "win_rate": 0.0,
            "full_loss_rate": 0.0,
            "mean_expected_edge": 0.0,
            "mean_roi_per_scan": 0.0,
        }

    rois = [float(b["roi_real"]) for b in bets]
    bet_rate = _safe_div(len(bets), total_scans)
    return {
        "scans": float(total_scans),
        "bets": float(len(bets)),
        "bet_rate": bet_rate,
        "mean_roi_per_bet": mean(rois),
        "median_roi_per_bet": median(rois),
        "win_rate": sum(1 for x in rois if x > 0) / len(rois),
        "full_loss_rate": sum(1 for x in rois if x <= -0.9) / len(rois),
        "mean_expected_edge": mean(float(b["expected_edge"]) for b in bets),
        "mean_roi_per_scan": mean(rois) * bet_rate,
    }


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
    total_scans = len({r["ts"] for r in feats})
    bets = pick_best_bets(rows, cfg)
    metrics = compute_metrics(bt)
    metrics.update(robustness_checks(bt, cfg))
    metrics.update(summarize_bets(bets, total_scans))
    return bt, metrics, bets


def compute_metrics(bt: list[dict]) -> dict[str, float]:
    pnl = [r["pnl"] for r in bt]
    if not pnl:
        return {"pnl_sharpe": 0.0, "pnl_max_drawdown": 0.0, "pnl_hit_rate": 0.0, "exposure": 0.0, "turnover": 0.0}

    eq = []
    cur = 1.0
    for p in pnl:
        cur *= 1 + p
        eq.append(cur)

    avg = mean(pnl)
    var = mean([(x - avg) ** 2 for x in pnl]) if pnl else 0.0
    std = math.sqrt(var)
    sharpe = math.sqrt(365 * 6) * avg / (std + 1e-12)

    peak = 1.0
    max_dd = 0.0
    for v in eq:
        peak = max(peak, v)
        max_dd = min(max_dd, v / peak - 1)

    return {
        "pnl_sharpe": sharpe,
        "pnl_max_drawdown": max_dd,
        "pnl_hit_rate": sum(1 for x in pnl if x > 0) / len(pnl),
        "exposure": sum(abs(r["position"]) for r in bt) / len(bt),
        "turnover": sum(r["trade_size"] for r in bt),
    }


def robustness_checks(bt: list[dict], cfg: BacktestConfig) -> dict[str, float]:
    out = {"oos_pnl_sharpe": 0.0, "walk_forward_mean_pnl": 0.0, "placebo_mean_pnl": 0.0, "cost_sensitivity_pnl": 0.0, "latency2_mean_pnl": 0.0}
    if not bt:
        return out

    n = len(bt)
    oos = [r["pnl"] for r in bt[int(0.7 * n) :]]
    if oos:
        m = mean(oos)
        s = math.sqrt(mean([(x - m) ** 2 for x in oos]))
        out["oos_pnl_sharpe"] = math.sqrt(365 * 6) * m / (s + 1e-12)

    split = max(n // max(cfg.walk_forward_splits, 1), 1)
    vals = []
    edges = [abs(r["edge"]) for r in bt]
    for i in range(split, n, split):
        tr = sorted(edges[:i])
        q = tr[int(0.7 * (len(tr) - 1))] if tr else 0.0
        test = [bt[j]["pnl"] for j in range(i, min(i + split, n)) if abs(bt[j]["edge"]) > q]
        if test:
            vals.append(mean(test))
    out["walk_forward_mean_pnl"] = mean(vals) if vals else 0.0

    rng = random.Random(42)
    by_day: dict[str, list[dict]] = {}
    for r in bt:
        by_day.setdefault(r["ts"][:10], []).append(r)
    placebo = []
    for rows in by_day.values():
        sigs = [r["signal"] for r in rows]
        rng.shuffle(sigs)
        for i, r in enumerate(rows):
            placebo.append(sigs[i] * r["ret"])
    out["placebo_mean_pnl"] = mean(placebo) if placebo else 0.0
    out["cost_sensitivity_pnl"] = mean([r["pnl"] - r["trade_size"] * 0.002 for r in bt])
    out["latency2_mean_pnl"] = mean([((bt[i - 2]["position"] if i >= 2 else 0.0) * bt[i]["ret"] - bt[i]["costs"]) for i in range(len(bt))])
    return out


def _rows_to_markdown(rows: list[dict], cols: list[str]) -> str:
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        vals = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                vals.append(f"{v:.4f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_report(metrics: dict[str, float], bets: list[dict], path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    key_order = [
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
    lines = ["# Backtest Summary", "", "## Bet-selection summary", "", "| Metric | Value |", "|---|---:|"]
    for k in key_order:
        if k in metrics:
            lines.append(f"| {k} | {metrics[k]:.6f} |")

    good = sorted(bets, key=lambda x: x.get("roi_real", -999), reverse=True)[:10]
    bad = sorted(bets, key=lambda x: x.get("roi_real", 999))[:10]

    lines += ["", "## Best realized bets (top 10)", ""]
    if good:
        lines.append(_rows_to_markdown(good, ["ts", "market_title", "bet_side", "mid", "expected_edge", "roi_real", "market_type"]))
    else:
        lines.append("No qualifying bets.")

    lines += ["", "## Worst realized bets (bottom 10)", ""]
    if bad:
        lines.append(_rows_to_markdown(bad, ["ts", "market_title", "bet_side", "mid", "expected_edge", "roi_real", "market_type"]))
    else:
        lines.append("No qualifying bets.")

    verdict = "yes" if metrics.get("mean_roi_per_bet", 0.0) > 0 and metrics.get("win_rate", 0.0) > 0.5 else "unclear"
    lines += ["", f"Final verdict on inefficiency evidence: **{verdict}**"]
    p.write_text("\n".join(lines))
