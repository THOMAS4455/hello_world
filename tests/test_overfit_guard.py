import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from validation.overfit_guard import (
    _norm_cdf,
    _norm_ppf,
    deflated_sharpe_ratio,
    ic_t_stat,
    pbo,
    psr,
    sharpe,
)


def test_norm_ppf_sanity():
    assert abs(_norm_ppf(0.975) - 1.96) < 0.01
    assert abs(_norm_cdf(1.96) - 0.975) < 0.001


def test_psr_high_for_positive_drift():
    rng = np.random.default_rng(0)
    returns = 0.003 + rng.standard_normal(1000) * 0.01
    assert psr(returns) > 0.95


def test_psr_not_significant_for_noise():
    rng = np.random.default_rng(1)
    returns = rng.standard_normal(1000) * 0.01
    assert psr(returns) < 0.95


def test_deflated_sharpe_decreases_with_trials():
    rng = np.random.default_rng(2)
    returns = 0.0008 + rng.standard_normal(300) * 0.01
    assert deflated_sharpe_ratio(returns, n_trials=20) <= deflated_sharpe_ratio(returns, n_trials=1)


def test_ic_t_stat_positive_signal():
    rng = np.random.default_rng(3)
    ic = 0.05 + rng.standard_normal(100) * 0.1
    assert ic_t_stat(ic) > 2.0


def test_pbo_in_range():
    rng = np.random.default_rng(4)
    R = rng.standard_normal((200, 5)) * 0.01
    assert 0.0 <= pbo(R) <= 1.0


def test_sharpe_annualization():
    rng = np.random.default_rng(5)
    returns = 0.0005 + rng.standard_normal(1000) * 0.01
    assert sharpe(returns) > 0
