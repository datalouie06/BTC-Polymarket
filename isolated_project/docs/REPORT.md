# Polymarket BTC Inefficiency Study

## Hypothesis
Polymarket BTC condition markets are inefficient versus a derivatives-informed reference probability, and this can be exploited through selective bet picking.

## Data sources
- **Polymarket** public Gamma API metadata/snapshots with caching and deterministic fallback when API access is unavailable.
- **Reference proxy** derived from free/public information and mapped to each market timestamp.

## Methodology (updated)
1. Ingest broad BTC markets and keep all BTC-tagged contracts; market type is tracked via `strike_or_condition` prefix (e.g., `above`, `touch`, `range`).
2. Compute edge at each timestamp:
   - `edge = reference_prob - polymarket_prob`
3. Two complementary evaluations:
   - **PnL process checks** (latency/cost-aware, no-lookahead signal simulation)
   - **Bet selection checks** (pick the best candidate per scan timestamp under rules)
4. Focus on interpretable decision metrics:
   - scans, bets, bet rate
   - mean/median ROI per bet
   - win rate, full-loss rate
   - mean expected edge, unconditional ROI per scan
5. Robustness:
   - walk-forward edge quantile selection
   - placebo signal shuffling
   - cost and latency sensitivity
   - OOS PnL Sharpe as supporting diagnostic only

## Why CAGR was removed
This workflow does not assume continuously investable equity with stable capital deployment. Contract-level binary bets and sparse bet timing make CAGR misleading, so the report now centers on bet-level outcomes and frequency.

## Results usage
Run:
```bash
make build_data
make backtest
```
Then inspect `docs/BACKTEST_SUMMARY.md` for:
- readable metric table
- top/bottom realized bet tables
- final verdict based on bet-level quality

## Failure modes / falsification checks
- Edge appears only in low-liquidity bins.
- Positive average edge but negative realized ROI after conservative fills.
- Placebo performs similarly to real signals.
- Strategy only works in-sample and collapses OOS.
