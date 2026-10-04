"""Cross-sectional momentum factor backtest for A-shares.

Pure function with no storage or network dependencies. The caller supplies a
``{symbol: OHLCV DataFrame}`` mapping and receives a metrics report. This keeps
the factor logic testable and reusable by scripts, API routes and batch jobs.

Methodology (no lookahead):
    * factor_t  = average of past-N-day returns, computed with ``shift(1)`` and
      ``shift(N+1)`` so it only uses data strictly before the rebalance close.
    * entry at close[t], forward return over close[t] -> close[t+horizon].
    * cross-sectional Spearman IC at every rebalance date.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from validation.overfit_guard import deflated_sharpe_ratio, ic_t_stat


def _prepare_close(df: pd.DataFrame) -> pd.Series:
    frame = df.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"])
    else:
        frame["date"] = frame.index
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    close_col = "close" if "close" in frame.columns else "close_price"
    frame = frame.dropna(subset=[close_col]).sort_values("date")
    return pd.Series(
        pd.to_numeric(frame[close_col], errors="coerce").values,
        index=pd.DatetimeIndex(frame["date"]),
        name=close_col,
    )


def _max_drawdown(equity: Sequence[float]) -> float:
    peak = -np.inf
    mdd = 0.0
    for v in equity:
        peak = max(peak, float(v))
        if peak > 0:
            mdd = max(mdd, (peak - float(v)) / peak)
    return mdd


def _annualize(per_period: float, horizon: int, periods_per_year: float = 252.0) -> float:
    return (1.0 + per_period) ** (periods_per_year / max(horizon, 1)) - 1.0


def run_momentum_backtest(
    histories: Dict[str, pd.DataFrame],
    *,
    lookback: Sequence[int] = (20, 60),
    horizon: int = 5,
    rebalance_every: int = 5,
    top_frac: float = 0.2,
    min_history: int = 80,
    n_trials: int = 1,
) -> Dict[str, Any]:
    """Run a cross-sectional momentum factor backtest.

    Returns a metrics report including mean IC, ICIR, top/bottom group returns,
    long-short excess, Sharpe and max drawdown. An empty/short universe returns
    an ``error`` key instead of fabricating a result.
    """
    series: Dict[str, pd.Series] = {}
    for symbol, df in histories.items():
        try:
            s = _prepare_close(df)
            if len(s) >= min_history:
                series[str(symbol)] = s
        except Exception:
            continue

    if len(series) < 5:
        return {"error": "insufficient symbols for cross-sectional ranking", "n_symbols": len(series)}

    lookback = tuple(int(x) for x in lookback)
    max_lb = max(lookback)

    momentum: Dict[str, pd.Series] = {}
    for symbol, s in series.items():
        acc = None
        for lb in lookback:
            m = s.shift(1) / s.shift(1 + lb) - 1.0
            acc = m if acc is None else acc.add(m, fill_value=0.0)
        momentum[symbol] = (acc / len(lookback)).dropna()

    all_dates = sorted(set().union(*[set(s.index) for s in series.values()]))

    ic_list: List[float] = []
    top_rets: List[float] = []
    bottom_rets: List[float] = []
    n_symbols_list: List[int] = []
    prev_top: Optional[set] = None
    turnover_sum = 0.0
    turnover_n = 0

    rebalance_dates = all_dates[max_lb + 1 :: rebalance_every]

    for t in rebalance_dates:
        idx = all_dates.index(t)
        if idx + horizon >= len(all_dates):
            break
        fwd_date = all_dates[idx + horizon]

        factors: Dict[str, float] = {}
        fwds: Dict[str, float] = {}
        for symbol, s in series.items():
            if t not in s.index or fwd_date not in s.index:
                continue
            mom_series = momentum.get(symbol)
            if mom_series is None or t not in mom_series.index:
                continue
            factor = float(mom_series.loc[t])
            fwd = float(s.loc[fwd_date] / s.loc[t] - 1.0)
            if not np.isfinite(factor) or not np.isfinite(fwd):
                continue
            factors[symbol] = factor
            fwds[symbol] = fwd

        if len(factors) < 10:
            continue

        fs = pd.Series(factors)
        fr = pd.Series(fwds)
        ic = float(fs.rank().corr(fr.rank()))
        if not np.isfinite(ic):
            continue

        ic_list.append(ic)
        n_symbols_list.append(len(fs))
        k = max(1, int(len(fs) * top_frac))
        top_syms = fs.sort_values(ascending=False).index[:k]
        bottom_syms = fs.sort_values(ascending=True).index[:k]
        top_rets.append(float(fr.loc[top_syms].mean()))
        bottom_rets.append(float(fr.loc[bottom_syms].mean()))

        top_set = set(top_syms)
        if prev_top is not None:
            overlap = len(top_set & prev_top) / max(k, 1)
            turnover_sum += 1.0 - overlap
            turnover_n += 1
        prev_top = top_set

    if not ic_list:
        return {"error": "no valid rebalance periods", "n_symbols": len(series)}

    ic_arr = np.asarray(ic_list)
    ic_mean = float(ic_arr.mean())
    ic_std = float(ic_arr.std(ddof=1)) if len(ic_arr) > 1 else 0.0
    icir = ic_mean / ic_std if ic_std > 1e-12 else 0.0

    top_mean = float(np.mean(top_rets))
    bottom_mean = float(np.mean(bottom_rets))
    ls_mean = top_mean - bottom_mean
    ppy = 252.0 / max(rebalance_every, 1)  # periods per year (non-overlapping)

    # top-group equity curve (per-period compounding) for Sharpe / drawdown
    equity = [1.0]
    for r in top_rets:
        equity.append(equity[-1] * (1.0 + float(r)))
    top_period_std = float(np.std(top_rets, ddof=1)) if len(top_rets) > 1 else 0.0
    top_sharpe = (float(np.mean(top_rets)) / top_period_std * np.sqrt(ppy)) if top_period_std > 1e-12 else 0.0

    ic_t = ic_t_stat(ic_list)
    dsr = deflated_sharpe_ratio(top_rets, n_trials=n_trials)
    passes_gate = bool(ic_t > 2 and ls_mean > 0 and dsr > 0.95)

    return {
        "factor": "cross_sectional_momentum",
        "lookback": list(lookback),
        "horizon": int(horizon),
        "rebalance_every": int(rebalance_every),
        "top_frac": float(top_frac),
        "n_symbols": len(series),
        "n_periods": len(ic_list),
        "avg_symbols_per_period": round(float(np.mean(n_symbols_list)), 1),
        "ic_mean": round(ic_mean, 6),
        "ic_std": round(ic_std, 6),
        "icir": round(icir, 4),
        "ic_positive_frac": round(float(np.mean(ic_arr > 0)), 4),
        "top_mean_return_per_period": round(top_mean, 6),
        "bottom_mean_return_per_period": round(bottom_mean, 6),
        "long_short_return_per_period": round(ls_mean, 6),
        "top_annualized_return": round(_annualize(top_mean, rebalance_every, 252.0), 6),
        "bottom_annualized_return": round(_annualize(bottom_mean, rebalance_every, 252.0), 6),
        "long_short_annualized": round(_annualize(ls_mean, rebalance_every, 252.0), 6),
        "top_sharpe": round(top_sharpe, 4),
        "top_max_drawdown": round(_max_drawdown(equity), 6),
        "turnover": round(turnover_sum / max(turnover_n, 1), 4) if turnover_n else 0.0,
        "ic_t_stat": round(ic_t, 4),
        "deflated_sharpe": round(dsr, 4),
        "passes_gate": passes_gate,
    }


def format_report(report: Dict[str, Any]) -> str:
    """Render the report as a short markdown block."""
    if "error" in report:
        return f"## 动量因子回测\n\n**失败**: {report['error']}（样本股票数 {report.get('n_symbols', 0)}）\n"
    lines = [
        "## 动量因子回测报告",
        "",
        f"- 因子：横截面动量（lookback={report['lookback']}，skip 1 日）",
        f"- 参数：horizon={report['horizon']}，rebalance={report['rebalance_every']}，top_frac={report['top_frac']}",
        f"- 样本：{report['n_symbols']} 只股票，{report['n_periods']} 个再平衡期，每期平均 {report['avg_symbols_per_period']} 只",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| IC 均值 | {report['ic_mean']} |",
        f"| ICIR | {report['icir']} |",
        f"| IC 为正占比 | {report['ic_positive_frac']} |",
        f"| Top 组每期收益 | {report['top_mean_return_per_period']} |",
        f"| Bottom 组每期收益 | {report['bottom_mean_return_per_period']} |",
        f"| 多空每期收益 | {report['long_short_return_per_period']} |",
        f"| Top 组年化 | {report['top_annualized_return']} |",
        f"| 多空年化 | {report['long_short_annualized']} |",
        f"| Top 组夏普 | {report['top_sharpe']} |",
        f"| Top 组最大回撤 | {report['top_max_drawdown']} |",
        f"| 换手率 | {report['turnover']} |",
        f"| IC t 值 | {report['ic_t_stat']} |",
        f"| Deflated Sharpe | {report['deflated_sharpe']} |",
        f"| 四门槛通过 | {'✅' if report['passes_gate'] else '❌'} |",
        "",
        "> 注：本回测基于当前存活股票，存在幸存者偏差（见 docs/SURVIVORSHIP_BIAS.md）。",
    ]
    return "\n".join(lines)
