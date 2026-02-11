# Polymarket BTC Inefficiency Study

## Hypothesis
Polymarket BTC binary/condition markets may be inefficient relative to a crypto derivatives-based proxy for risk-neutral probabilities.

## Data sources
- **Polymarket** public Gamma API market metadata (cached under `data/raw/`).
- **Reference proxy**: Deribit public option summary endpoint (free/public). If unavailable, the pipeline uses a deterministic synthetic proxy from the observed Polymarket probability path and time-to-expiry adjustment.

## Methodology
1. Ingest BTC-related markets and retain at least two market condition styles (e.g., `above` and `touch/range`, or deterministic fallback synthetic equivalents when API data is sparse).
2. Build timestamped market snapshots with bid/ask/mid/volume/liquidity and estimated fees.
3. Map reference probabilities to each timestamp and compute edge:
   - `edge = reference_prob - polymarket_prob`
4. Trading simulation:
   - enter long when edge exceeds threshold, short when below negative threshold
   - use latency-shifted positions (no lookahead)
   - apply transaction costs and spread/slippage penalties
   - cap position size and allow flat exits
5. Evaluate performance and robustness:
   - Sharpe, CAGR, max drawdown, hit rate, avg trade return, exposure, turnover
   - walk-forward threshold tuning
   - placebo signal shuffling within day
   - sensitivity to higher costs and added latency
   - out-of-sample Sharpe for final 30% of sample

## Results
Run:
```bash
make build_data
make backtest
```
Then inspect `docs/BACKTEST_SUMMARY.md` for final metrics and verdict.

## Failure modes and falsification checks
- **Reference mismatch risk**: options-implied proxies may not perfectly map to Polymarket payoff conventions.
- **Microstructure effects**: sparse liquidity can invalidate executable prices.
- **Latency/cost fragility**: edge may vanish under stricter fills.
- **Placebo check**: if shuffled signals produce similar PnL, evidence is weak.
- **Out-of-sample degradation**: significant OOS deterioration falsifies stable inefficiency.
