"""Causal A-share screening logic adapted from the local QuantA demo.

This module has no storage or web dependencies. It can therefore be reused by
batch jobs, API routes and backtests without creating a second data pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from research.screener_config import (
    FACTOR_W_LIQUIDITY,
    FACTOR_W_MOMENTUM,
    FACTOR_W_STABILITY,
    FACTOR_W_TREND,
)


def _normalise(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy().rename(columns={
        "date": "trade_date", "open_price": "open", "high_price": "high",
        "low_price": "low", "close_price": "close",
    })
    required = {"trade_date", "close", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("history is missing columns: {}".format(", ".join(sorted(missing))))
    for col in ("open", "high", "low"):
        if col not in frame:
            frame[col] = frame["close"]
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["trade_date", "close"]).sort_values("trade_date").reset_index(drop=True)
    if len(frame) < 20:
        raise ValueError("at least 20 valid daily bars are required")
    return frame


def _features(bars: pd.DataFrame) -> pd.DataFrame:
    frame = _normalise(bars)
    close = frame["close"]
    previous = close.shift(1)
    true_range = pd.concat([
        frame["high"] - frame["low"],
        (frame["high"] - previous).abs(),
        (frame["low"] - previous).abs(),
    ], axis=1).max(axis=1)
    frame["ma20"] = close.rolling(20, min_periods=20).mean()
    frame["ma60"] = close.rolling(60, min_periods=60).mean()
    frame["atr14"] = true_range.rolling(14, min_periods=14).mean()
    frame["atr_pct"] = frame["atr14"] / close
    frame["return20"] = close.pct_change(20)
    frame["return60"] = close.pct_change(60)
    frame["volume_ma20"] = frame["volume"].rolling(20, min_periods=20).mean()
    change = close.diff()
    gains = change.clip(lower=0).rolling(14, min_periods=14).mean()
    losses = (-change.clip(upper=0)).rolling(14, min_periods=14).mean()
    frame["rsi14"] = 100 - (100 / (1 + gains / losses.replace(0, np.nan)))
    return frame


def _float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if np.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _rank(snapshot: pd.DataFrame, min_score: float) -> pd.DataFrame:
    required = {"symbol", "close", "return20", "return60", "atr_pct", "volume", "volume_ma20", "ma20", "ma60"}
    missing = required - set(snapshot.columns)
    if missing:
        raise ValueError("snapshot is missing columns: {}".format(", ".join(sorted(missing))))
    frame = snapshot.dropna(subset=list(required)).copy()
    if frame.empty:
        return frame
    momentum = (frame["return20"].rank(pct=True) + frame["return60"].rank(pct=True)) / 2
    trend = ((frame["close"] > frame["ma20"]).astype(float) + (frame["ma20"] > frame["ma60"]).astype(float)) / 2
    liquidity = (frame["volume"] / frame["volume_ma20"]).clip(0, 3) / 3
    stability = 1 - frame["atr_pct"].rank(pct=True)
    frame["momentum_score"], frame["trend_score"] = momentum, trend
    frame["liquidity_score"], frame["stability_score"] = liquidity, stability
    frame["score"] = (
        FACTOR_W_MOMENTUM * momentum
        + FACTOR_W_TREND * trend
        + FACTOR_W_LIQUIDITY * liquidity
        + FACTOR_W_STABILITY * stability
    )
    frame["signal"] = frame["score"] >= min_score
    return frame.sort_values(["signal", "score"], ascending=[False, False]).reset_index(drop=True)


def build_candidate_report(
    histories: Dict[str, pd.DataFrame],
    predictions: Optional[Dict[str, Dict[str, Any]]] = None,
    min_score: float = .60,
    top_n: int = 10,
    market_regime: str = "normal",
) -> List[Dict[str, Any]]:
    """Return explainable conditional candidates from a point-in-time snapshot."""
    rows = []
    for symbol, history in histories.items():
        try:
            row = _features(history).iloc[-1].to_dict()
            row["symbol"] = str(symbol)
            rows.append(row)
        except (ValueError, IndexError):
            continue
    if not rows:
        return []
    ranked = _rank(pd.DataFrame(rows), min_score).query("signal").head(max(1, top_n))
    predictions = predictions or {}
    result = []
    for row in ranked.to_dict("records"):
        symbol, close, atr = str(row["symbol"]), _float(row["close"]), _float(row["atr14"])
        prediction = predictions.get(symbol) or {}
        defensive = market_regime == "defensive"
        result.append({
            "symbol": symbol,
            "score": round(_float(row["score"]), 4),
            "action": "observe" if defensive else "conditional_buy",
            "entry_low": round(close * .995, 2),
            "entry_high": round(close * 1.015, 2),
            "stop_price": round(max(close - 2 * atr, close * .92, .01), 2),
            "max_position_fraction": 0.0 if defensive else .05,
            "confidence": round(_float(prediction.get("confidence")), 4),
            "direction": prediction.get("direction", ""),
            "rationale": {
                "momentum_score": round(_float(row.get("momentum_score")), 4),
                "trend_score": round(_float(row.get("trend_score")), 4),
                "liquidity_score": round(_float(row.get("liquidity_score")), 4),
                "stability_score": round(_float(row.get("stability_score")), 4),
                "return20": round(_float(row.get("return20")), 4),
                "return60": round(_float(row.get("return60")), 4),
                "atr_pct": round(_float(row.get("atr_pct")), 4),
                "market_regime": market_regime,
                "invalidation": "close_below_stop_or_regime_defensive",
            },
        })
    return result


def analyze_holding(
    symbol: str, history: pd.DataFrame, quantity: int, available_quantity: int,
    average_cost: float, prediction: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a non-executing holding decision with concrete risk parameters."""
    if quantity <= 0 or average_cost <= 0:
        raise ValueError("quantity and average_cost must be positive")
    row = _features(history).iloc[-1]
    close, atr = _float(row["close"]), _float(row.get("atr14"))
    ma20, ma60, rsi = _float(row.get("ma20")), _float(row.get("ma60")), _float(row.get("rsi14"))
    prediction = prediction or {}
    direction, confidence = str(prediction.get("direction") or ""), _float(prediction.get("confidence"))
    pnl_pct = close / average_cost - 1
    stop = max(close - 2 * atr, average_cost * .92, .01)
    trailing_stop = max(average_cost, close - 2 * atr) if pnl_pct >= .08 else stop
    exit_risk = max(close - stop, .01)
    take_profit_1 = round(close + 1.0 * exit_risk, 2)
    take_profit_2 = round(close + 2.0 * exit_risk, 2)
    available = max(0, min(int(available_quantity), int(quantity)))
    action, reduce_pct, reasons = "hold", 0.0, []
    if close <= stop:
        action, reduce_pct = ("reduce" if available else "observe"), (1.0 if available else 0.0)
        reasons.append("price_below_atr_risk_line")
    elif ma20 > 0 and ma60 > 0 and close < ma20 < ma60:
        action, reduce_pct = ("reduce" if available else "observe"), (.5 if available else 0.0)
        reasons.append("close_below_ma20_and_ma60")
    elif direction == "down" and confidence >= .60:
        action, reduce_pct = ("reduce" if available else "observe"), (.3 if available else 0.0)
        reasons.append("high_confidence_down_prediction")
    elif pnl_pct >= .15 and rsi >= 70:
        action, reduce_pct = ("reduce" if available else "observe"), (.3 if available else 0.0)
        reasons.append("extended_profit_and_overbought_rsi")
    elif direction == "up" and confidence >= .60 and close > ma20 > ma60:
        reasons.append("up_prediction_with_confirmed_trend")
    else:
        reasons.append("no_confirmed_exit_or_add_signal")
    return {
        "symbol": str(symbol), "action": action, "quantity": int(quantity),
        "available_quantity": available, "average_cost": round(average_cost, 2),
        "current_price": round(close, 2), "profit_loss_pct": round(pnl_pct, 4),
        "ma20": round(ma20, 2), "ma60": round(ma60, 2), "rsi14": round(rsi, 2),
        "atr14": round(atr, 2), "stop_price": round(stop, 2),
        "trailing_stop_price": round(trailing_stop, 2), "suggested_reduce_pct": reduce_pct,
        "take_profit_1": take_profit_1, "take_profit_2": take_profit_2,
        "risk_reward_ratio": round(2.0, 2),
        "prediction_direction": direction, "prediction_confidence": round(confidence, 4),
        "reasons": reasons,
        "research_note": "For research only; confirm market conditions and executable quantity before trading.",
    }


def build_entry_plan(
    symbol: str,
    history: pd.DataFrame,
    prediction: Optional[Dict[str, Any]] = None,
    capital: float = 100_000.0,
    max_position_pct: float = 0.05,
    name: str = "",
) -> Dict[str, Any]:
    """Return parameter-level entry/exit/position advice for one candidate stock.

    Every figure is concrete: entry zone, stop loss, a 1R/2R/3R take-profit
    ladder, and a position size expressed in both shares and 100-share lots
    (A-share lot size), plus the resulting risk/reward and capital allocation.
    """
    row = _features(history).iloc[-1]
    close = _float(row["close"])
    atr = _float(row.get("atr14"))
    if atr <= 0:
        atr = close * 0.02
    ma20 = _float(row.get("ma20"))
    ma60 = _float(row.get("ma60"))
    rsi = _float(row.get("rsi14"))
    prediction = prediction or {}
    direction = str(prediction.get("direction") or "")
    confidence = _float(prediction.get("confidence"))
    trade_allowed = bool(prediction.get("trade_allowed", False))
    ensemble_up = _float((prediction.get("layer_outputs") or {}).get("ensemble_up"))

    entry = close
    entry_min = round(close * 0.995, 2)
    entry_max = round(close * 1.015, 2)
    stop = round(max(close - 2 * atr, close * 0.92, 0.01), 2)
    risk_per_share = max(entry - stop, 0.01)

    # Take-profit ladder: R = entry - stop (per-share risk)
    take_profit_1 = round(entry + 1.0 * risk_per_share, 2)
    take_profit_2 = round(entry + 2.0 * risk_per_share, 2)
    take_profit_3 = round(entry + 3.0 * risk_per_share, 2)

    # Position sizing: risk 1% of capital per trade, capped by max_position_pct
    capital = max(_float(capital), 0.0)
    risk_budget = capital * 0.01
    shares = int(risk_budget / risk_per_share) if risk_per_share > 0 else 0
    if close > 0 and max_position_pct > 0:
        max_shares = int(capital * max_position_pct / close)
        shares = min(shares, max_shares)
    lots = shares // 100
    shares = lots * 100
    position_pct = round(shares * close / capital, 4) if capital > 0 else 0.0
    notional = round(shares * close, 2)

    reasons: List[str] = []
    if not trade_allowed:
        action = "observe"
        reasons.append("trade_not_allowed_by_signal_gate")
    elif direction != "up":
        action = "observe"
        reasons.append("prediction_direction_not_up")
    elif confidence < 0.55:
        action = "observe"
        reasons.append("confidence_below_55pct")
    elif ma20 > 0 and ma60 > 0 and close > ma20 > ma60:
        action = "buy"
        reasons.append("price_above_ma20_above_ma60")
    else:
        action = "conditional_buy"
        reasons.append("trend_not_fully_confirmed")

    return {
        "symbol": str(symbol),
        "name": str(name or ""),
        "action": action,
        "entry_price": round(entry, 2),
        "entry_zone": [entry_min, entry_max],
        "stop_loss": stop,
        "take_profit_1": take_profit_1,
        "take_profit_2": take_profit_2,
        "take_profit_3": take_profit_3,
        "risk_reward_ratio": round(2.0, 2),
        "position_pct": position_pct,
        "position_shares": shares,
        "position_lots": lots,
        "position_notional": notional,
        "current_price": round(close, 2),
        "atr14": round(atr, 2),
        "ma20": round(ma20, 2),
        "ma60": round(ma60, 2),
        "rsi14": round(rsi, 2),
        "prediction_direction": direction,
        "prediction_confidence": round(confidence, 4),
        "ensemble_up": round(ensemble_up, 4),
        "invalidation": "close_below_stop_loss",
        "reasons": reasons,
    }
