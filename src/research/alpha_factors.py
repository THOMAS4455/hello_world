"""Alpha158-style daily factor set (the OHLCV-only subset).

Qlib's Alpha158 is a proven, benchmarked feature set for stock prediction. This
module implements the subset that can be computed from daily OHLCV + volume
only (~40 factors), grouped by category:

    * returns / ROC
    * rolling mean / std / max / min of price
    * price vs moving-average position
    * volume & turnover ratios
    * amplitude / K-line shape (shadows, body, close position)
    * realized volatility
    * RSI / MACD / Bollinger / KDJ

All factors are computed with ``rolling`` / ``shift`` / ``pct_change`` so they
use only information available at or before the current bar (no lookahead).
"""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    rename = {
        "open_price": "open",
        "high_price": "high",
        "low_price": "low",
        "close_price": "close",
    }
    frame = frame.rename(columns=rename)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"]).sort_values("date")
        frame = frame.set_index("date")
    for col in ("open", "high", "low", "close", "volume"):
        if col not in frame.columns:
            if col == "close" and "close" not in frame.columns:
                raise ValueError("missing 'close' column")
            if col == "volume":
                frame[col] = 0.0
            elif col in ("open", "high", "low") and "close" in frame.columns:
                frame[col] = frame["close"]
    for col in ("open", "high", "low", "close", "volume"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["amount"] = frame["close"] * frame["volume"]
    return frame


def compute_alpha_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of Alpha158-style factors indexed by date."""
    f = _normalize(df)
    close, high, low, open_ = f["close"], f["high"], f["low"], f["open"]
    volume, amount = f["volume"], f["amount"]
    out = pd.DataFrame(index=f.index)

    # --- returns ---
    out["ret_1"] = close.pct_change(1)
    out["ret_5"] = close.pct_change(5)
    out["ret_10"] = close.pct_change(10)
    out["ret_20"] = close.pct_change(20)

    # --- rolling mean of price ---
    for w in (5, 10, 20, 30):
        out[f"ma_{w}"] = close.rolling(w, min_periods=w).mean()
    # --- rolling std of price ---
    for w in (5, 10, 20):
        out[f"std_{w}"] = close.rolling(w, min_periods=w).std()
    # --- rolling max / min ---
    out["max_10"] = close.rolling(10, min_periods=10).max()
    out["min_10"] = close.rolling(10, min_periods=10).min()

    # --- price vs MA position ---
    out["close_over_ma5"] = close / out["ma_5"] - 1.0
    out["close_over_ma10"] = close / out["ma_10"] - 1.0
    out["close_over_ma20"] = close / out["ma_20"] - 1.0

    # --- volume & turnover ratios ---
    out["vol_ratio_5"] = volume / volume.rolling(5, min_periods=5).mean()
    out["vol_ratio_20"] = volume / volume.rolling(20, min_periods=20).mean()
    out["amount_ratio_5"] = amount / amount.rolling(5, min_periods=5).mean()
    out["amount_ratio_20"] = amount / amount.rolling(20, min_periods=20).mean()

    # --- amplitude / K-line shape ---
    out["amplitude"] = (high - low) / close
    out["hl_ratio"] = high / low
    upper = high - np.maximum(open_, close)
    lower = np.minimum(open_, close) - low
    out["upper_shadow"] = upper / close
    out["lower_shadow"] = lower / close
    out["body"] = (close - open_).abs() / close
    denom = (high - low).replace(0, np.nan)
    out["close_position"] = (close - low) / denom

    # --- realized volatility (std of daily returns) ---
    for w in (5, 10, 20):
        out[f"vol_{w}"] = close.pct_change(1).rolling(w, min_periods=w).std()

    # --- ROC (same as ret but explicit) ---
    out["roc_5"] = close / close.shift(5) - 1.0
    out["roc_10"] = close / close.shift(10) - 1.0
    out["roc_20"] = close / close.shift(20) - 1.0
    out["roc_60"] = close / close.shift(60) - 1.0

    # --- RSI(14) ---
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi_14"] = 100 - 100 / (1 + rs)

    # --- MACD ---
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd"] = macd
    out["macd_signal"] = macd.ewm(span=9, adjust=False).mean()

    # --- Bollinger position ---
    ma20 = close.rolling(20, min_periods=20).mean()
    std20 = close.rolling(20, min_periods=20).std()
    out["boll_pos"] = (close - ma20) / (2 * std20)

    # --- KDJ ---
    low9 = low.rolling(9, min_periods=1).min()
    high9 = high.rolling(9, min_periods=1).max()
    rsv = (close - low9) / (high9 - low9 + 1e-9) * 100
    out["kdj_k"] = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    out["kdj_d"] = out["kdj_k"].ewm(alpha=1 / 3, adjust=False).mean()

    # --- correlation between price and volume ---
    out["corr_close_vol_20"] = close.rolling(20, min_periods=20).corr(volume)

    out = out.replace([np.inf, -np.inf], np.nan)
    return out


FACTOR_NAMES: List[str] = [
    "ret_1", "ret_5", "ret_10", "ret_20",
    "ma_5", "ma_10", "ma_20", "ma_30",
    "std_5", "std_10", "std_20",
    "max_10", "min_10",
    "close_over_ma5", "close_over_ma10", "close_over_ma20",
    "vol_ratio_5", "vol_ratio_20", "amount_ratio_5", "amount_ratio_20",
    "amplitude", "hl_ratio", "upper_shadow", "lower_shadow", "body", "close_position",
    "vol_5", "vol_10", "vol_20",
    "roc_5", "roc_10", "roc_20", "roc_60",
    "rsi_14", "macd", "macd_signal", "boll_pos", "kdj_k", "kdj_d",
    "corr_close_vol_20",
]
