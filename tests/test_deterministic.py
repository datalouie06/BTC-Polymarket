from polymarket_btc.backtest import BacktestConfig, simulate_backtest
from polymarket_btc.dataset import build_dataset


def test_deterministic_fixed_range(tmp_path):
    rows1 = build_dataset(str(tmp_path / "a.parquet"), start="2024-01-01", end="2024-01-10")
    rows2 = build_dataset(str(tmp_path / "b.parquet"), start="2024-01-01", end="2024-01-10")
    assert rows1 == rows2

    _, m1 = simulate_backtest(rows1, BacktestConfig())
    _, m2 = simulate_backtest(rows2, BacktestConfig())
    assert m1 == m2
