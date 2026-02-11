from polymarket_btc.backtest import BacktestConfig, simulate_backtest
from polymarket_btc.dataset import build_dataset


def test_positions_are_lagged(tmp_path):
    rows = build_dataset(str(tmp_path / "d.parquet"), start="2024-01-01", end="2024-01-05")
    bt, _ = simulate_backtest(rows, BacktestConfig(latency_steps=1, entry_threshold=0.01))
    subset = [r for r in bt if r["market_id"] == bt[0]["market_id"] and r["side"] == bt[0]["side"]]
    for i in range(1, len(subset)):
        if subset[i - 1]["signal"] != 0 and abs(subset[i - 1]["edge"]) >= 0.01:
            assert subset[i]["position"] == subset[i - 1]["signal"] or subset[i]["position"] == 0.0
