from polymarket_btc.backtest import BacktestConfig, simulate_backtest
from polymarket_btc.dataset import build_dataset


def test_bet_selection_metrics_present(tmp_path):
    rows = build_dataset(str(tmp_path / "d.parquet"), start="2024-01-01", end="2024-01-10")
    _, metrics, bets = simulate_backtest(rows, BacktestConfig())
    assert "mean_roi_per_bet" in metrics
    assert "bet_rate" in metrics
    assert "pnl_sharpe" in metrics
    assert "cagr" not in metrics
    assert isinstance(bets, list)
