from polymarket_btc.dataset import REQUIRED_COLUMNS, build_dataset


def test_dataset_schema(tmp_path):
    out = tmp_path / "dataset.parquet"
    rows = build_dataset(str(out), start="2024-01-01", end="2024-01-07")
    assert out.exists()
    assert len(rows) > 0
    assert all(set(r.keys()) == set(REQUIRED_COLUMNS) for r in rows)
    assert set(r["side"] for r in rows) <= {"yes", "no"}
