"""Backtest-overfitting guards (Bailey & López de Prado).

Implements the statistics that keep a factor/strategy search honest:

* ``psr`` — Probabilistic Sharpe Ratio: probability the true Sharpe exceeds a
  benchmark (usually 0), accounting for skew/kurtosis of the return stream.
* ``deflated_sharpe_ratio`` — PSR after correcting for ``n_trials`` (the number
  of strategies/factors that were tried), so "we tested 20 things and one
  looked good" no longer passes as luck-free.
* ``pbo`` — Probability of Backtest Overfitting via Combinatorially Symmetric
  Cross-Validation (CSCV): how often the in-sample winner is in the bottom half
  out-of-sample.

Pure stdlib + numpy; no new dependencies.
"""

from __future__ import annotations

import itertools
import math
from typing import Sequence

import numpy as np

_EULER_GAMMA = 0.5772156649015329
_E = math.e


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation)."""
    if p <= 0.0:
        return -8.0
    if p >= 1.0:
        return 8.0
    a = [
        -3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
        1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
        6.680131188771972e01, -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
        -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif p <= phigh:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    return x


def _skew(x: np.ndarray) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    m = float(x.mean())
    s = float(x.std(ddof=1))
    if s < 1e-12:
        return 0.0
    return float((np.sum((x - m) ** 3) / n) / (s ** 3))


def _kurt(x: np.ndarray) -> float:
    n = len(x)
    if n < 4:
        return 3.0
    m = float(x.mean())
    s = float(x.std(ddof=1))
    if s < 1e-12:
        return 3.0
    return float((np.sum((x - m) ** 4) / n) / (s ** 4))


def sharpe(returns: Sequence[float], periods_per_year: int = 252) -> float:
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2:
        return 0.0
    sd = float(arr.std(ddof=1))
    if sd < 1e-12:
        return 0.0
    return float(arr.mean() / sd * math.sqrt(periods_per_year))


def _psr(sr: float, skew: float, kurt: float, n: int, benchmark_sr: float) -> float:
    if n < 2:
        return 0.0
    num = (sr - benchmark_sr) * math.sqrt(n - 1)
    den = math.sqrt(max(1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2, 1e-12))
    return _norm_cdf(num / den)


def psr(returns: Sequence[float], benchmark_sr: float = 0.0) -> float:
    """Probability the true per-period Sharpe exceeds ``benchmark_sr``."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2:
        return 0.0
    sd = float(arr.std(ddof=1))
    if sd < 1e-12:
        return 0.0
    sr = float(arr.mean() / sd)
    return _psr(sr, _skew(arr), _kurt(arr), len(arr), benchmark_sr)


def deflated_sharpe_ratio(returns: Sequence[float], n_trials: int = 1) -> float:
    """Deflated Sharpe Ratio: PSR after correcting for ``n_trials`` tests."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2:
        return 0.0
    sd = float(arr.std(ddof=1))
    if sd < 1e-12:
        return 0.0
    sr = float(arr.mean() / sd)
    skew, kurt, n = _skew(arr), _kurt(arr), len(arr)
    if n_trials <= 1:
        return _psr(sr, skew, kurt, n, 0.0)

    var_sr = max(1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2, 0.0) / (n - 1)
    std_sr = math.sqrt(var_sr)
    z1 = _norm_ppf(1.0 - 1.0 / n_trials)
    z2 = _norm_ppf(1.0 - 1.0 / (n_trials * _E))
    sr0 = std_sr * ((1.0 - _EULER_GAMMA) * z1 + _EULER_GAMMA * z2)
    return _psr(sr, skew, kurt, n, sr0)


def ic_t_stat(ic_series: Sequence[float]) -> float:
    """t-statistic of a mean IC series (mean / standard error)."""
    arr = np.asarray(ic_series, dtype=float)
    if len(arr) < 2:
        return 0.0
    se = float(arr.std(ddof=1) / math.sqrt(len(arr)))
    if se < 1e-12:
        return 0.0
    return float(arr.mean() / se)


def pbo(returns_matrix: Sequence[Sequence[float]], n_blocks: int = 16, max_combos: int = 2000) -> float:
    """Probability of Backtest Overfitting via CSCV.

    ``returns_matrix`` is shaped (n_observations, n_strategies): each column is
    one strategy's return stream over the same period. A result >= 0.5 means the
    in-sample winner is more often than not in the bottom half out-of-sample
    (i.e. the selection is overfit).
    """
    R = np.asarray(returns_matrix, dtype=float)
    if R.ndim == 1:
        R = R.reshape(1, -1)
    if R.shape[0] < R.shape[1]:
        R = R.T
    n_obs, n_strat = R.shape
    if n_obs < 8 or n_strat < 2:
        return 0.0

    n_blocks = max(2, min(int(n_blocks), n_obs // 2))
    if n_blocks % 2:
        n_blocks -= 1
    if n_blocks < 2:
        return 0.0
    block_len = n_obs // n_blocks
    blocks = [R[i * block_len:(i + 1) * block_len] for i in range(n_blocks)]
    half = n_blocks // 2

    combos = list(itertools.combinations(range(n_blocks), half))
    if len(combos) > max_combos:
        rng = np.random.default_rng(0)
        idx = rng.choice(len(combos), max_combos, replace=False)
        combos = [combos[int(i)] for i in idx]

    below_median = 0
    total = 0
    for combo in combos:
        is_idx = list(combo)
        oos_idx = [i for i in range(n_blocks) if i not in combo]
        is_ret = np.concatenate([blocks[i] for i in is_idx])
        oos_ret = np.concatenate([blocks[i] for i in oos_idx])

        def _sr(col: np.ndarray) -> float:
            sd = float(col.std(ddof=1))
            return float(col.mean() / sd) if sd > 1e-12 else 0.0

        is_sr = np.array([_sr(is_ret[:, j]) for j in range(n_strat)])
        oos_sr = np.array([_sr(oos_ret[:, j]) for j in range(n_strat)])
        best = int(np.argmax(is_sr))
        rel_rank = float(np.sum(oos_sr < oos_sr[best]) / (n_strat - 1)) if n_strat > 1 else 1.0
        if rel_rank < 0.5:
            below_median += 1
        total += 1

    return below_median / total if total else 0.0
