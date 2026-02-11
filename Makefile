PYTHON ?= python3
export PYTHONPATH := src

.PHONY: setup build_data test backtest

setup:
	$(PYTHON) -m pip install -r requirements.txt

build_data:
	$(PYTHON) -m polymarket_btc.cli build-data --output data/processed/pm_btc_reference.parquet

test:
	pytest -q

backtest:
	$(PYTHON) -m polymarket_btc.cli backtest --dataset data/processed/pm_btc_reference.parquet --report docs/BACKTEST_SUMMARY.md
