from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_name(url: str, params: dict[str, Any] | None = None) -> str:
    payload = {"url": url, "params": params or {}}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"{digest}.json"


def fetch_json_with_cache(
    url: str,
    params: dict[str, Any] | None = None,
    cache_dir: str | Path = "data/raw",
    retries: int = 3,
    timeout: int = 20,
) -> Any:
    cache_path = ensure_dir(cache_dir) / _cache_name(url, params)
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    err: Exception | None = None
    for i in range(retries):
        try:
            res = requests.get(url, params=params, timeout=timeout)
            res.raise_for_status()
            data = res.json()
            cache_path.write_text(json.dumps(data))
            return data
        except Exception as exc:  # network robustness
            err = exc
            time.sleep(1.5**i)

    if cache_path.exists():
        return json.loads(cache_path.read_text())
    raise RuntimeError(f"Failed to fetch {url} after retries") from err
