import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd

from research.alpha_factors import FACTOR_NAMES, compute_alpha_factors


def _make_df(n=300, seed=0):
    rng = np.random.default_rng(seed)
    close = 20 * np.exp(np.cumsum(rng.standard_normal(n) * 0.01))
    open_ = close * (1 + rng.standard_normal(n) * 0.005)
    high = np.maximum(open_, close) * (1 + np.abs(rng.standard_normal(n)) * 0.005)
    low = np.minimum(open_, close) * (1 - np.abs(rng.standard_normal(n)) * 0.005)
    volume = rng.integers(100000, 1000000, n)
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=n),
            "open_price": open_,
            "high_price": high,
            "low_price": low,
            "close_price": close,
            "volume": volume,
        }
    )


def test_factor_count():
    out = compute_alpha_factors(_make_df())
    assert len(out.columns) >= 40
    assert set(FACTOR_NAMES).issubset(set(out.columns))


def test_no_lookahead():
    df = _make_df(220)
    full = compute_alpha_factors(df)
    truncated = compute_alpha_factors(df.iloc[:180])
    a = full.iloc[:150]
    b = truncated.iloc[:150]
    # Factor values at time t must not depend on any future bar.
    assert np.allclose(a.values, b.values, equal_nan=True, rtol=0, atol=0)


def test_finite_after_warmup():
    out = compute_alpha_factors(_make_df(300))
    tail = out.iloc[100:]
    assert not np.isinf(tail.values).any()
    finite_frac = np.isfinite(tail.values).mean()
    assert finite_frac > 0.9
