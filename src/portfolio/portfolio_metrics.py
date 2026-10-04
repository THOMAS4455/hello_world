"""Portfolio performance metrics (VectorBT-style, lightweight)."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _max_drawdown(equity: List[float]) -> Dict[str, float]:
    if not equity:
        return {"max_drawdown": 0.0, "max_drawdown_duration": 0}
    peak = equity[0]
    max_dd = 0.0
    duration = 0
    cur_duration = 0
    for v in equity:
        if v > peak:
            peak = v
            cur_duration = 0
        else:
            cur_duration += 1
            dd = (peak - v) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
                duration = cur_duration
    return {"max_drawdown": max_dd, "max_drawdown_duration": duration}


def _daily_returns(equity: List[float]) -> List[float]:
    rets = []
    for i in range(1, len(equity)):
        prev = equity[i - 1] or 1.0
        rets.append(equity[i] / prev - 1.0)
    return rets


def compute_metrics(
    equity_curve: List[float],
    *,
    trading_days_per_year: int = 252,
    risk_free_rate: float = 0.02,
) -> Dict[str, Any]:
    if not equity_curve or len(equity_curve) < 2:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "days": 0,
        }

    rets = _daily_returns(equity_curve)
    n = len(rets)
    total_return = equity_curve[-1] / equity_curve[0] - 1.0 if equity_curve[0] else 0.0
    ann_factor = trading_days_per_year / max(n, 1)
    ann_return = (1.0 + total_return) ** ann_factor - 1.0 if n > 0 else 0.0

    mean_r = sum(rets) / n
    var = sum((r - mean_r) ** 2 for r in rets) / max(n - 1, 1)
    vol = math.sqrt(var) * math.sqrt(trading_days_per_year)

    rf_daily = risk_free_rate / trading_days_per_year
    excess = [r - rf_daily for r in rets]
    excess_mean = sum(excess) / n
    sharpe = (excess_mean / math.sqrt(var) * math.sqrt(trading_days_per_year)) if var > 1e-12 else 0.0

    downside = [min(0.0, r - rf_daily) for r in rets]
    down_var = sum(d ** 2 for d in downside) / max(n, 1)
    sortino = (excess_mean / math.sqrt(down_var) * math.sqrt(trading_days_per_year)) if down_var > 1e-12 else 0.0

    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r < 0]
    win_rate = len(wins) / n if n else 0.0
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = gross_win / gross_loss if gross_loss > 1e-12 else (gross_win if gross_win > 0 else 0.0)

    dd = _max_drawdown(equity_curve)

    return {
        "total_return": round(total_return, 6),
        "annualized_return": round(ann_return, 6),
        "volatility": round(vol, 6),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "max_drawdown": round(dd["max_drawdown"], 6),
        "max_drawdown_duration": int(dd["max_drawdown_duration"]),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "days": n,
    }


def compare_strategies(
    strategy_curve: List[float],
    benchmark_curve: List[float],
) -> Dict[str, Any]:
    strat = compute_metrics(strategy_curve)
    bench = compute_metrics(benchmark_curve)
    return {
        "strategy": strat,
        "benchmark": bench,
        "excess_return": round(
            (strategy_curve[-1] / strategy_curve[0] - 1.0)
            - (benchmark_curve[-1] / benchmark_curve[0] - 1.0)
            if strategy_curve and benchmark_curve and strategy_curve[0] and benchmark_curve[0]
            else 0.0,
            6,
        ),
    }
