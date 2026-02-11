# Isolated project copy (conflict-avoidance)

This folder is a full, self-contained copy of the BTC Polymarket research pipeline.
It exists so changes can be made and merged without touching the existing top-level
project files.

## Run from this folder

```bash
cd isolated_project
make setup
make test
make build_data
make backtest
```

## Colab usage

Use notebook:

- `isolated_project/notebooks/polymarket_btc_inefficiency_backtest.ipynb`

When setting repo paths in Colab, point to:

- `/content/BTC-Polymarket/isolated_project`

and add to `sys.path`:

```python
sys.path.insert(0, "/content/BTC-Polymarket/isolated_project/src")
```
