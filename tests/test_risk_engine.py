import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from portfolio.risk_engine import RiskEngine


def test_drawdown_multiplier():
    e = RiskEngine(max_drawdown=0.15, max_drawdown_critical=0.25)
    assert e.drawdown_multiplier([1.0, 1.0, 1.0]) == 1.0
    # 20% drawdown -> (0.25 - 0.20) / (0.25 - 0.15) = 0.5
    assert abs(e.drawdown_multiplier([1.0, 0.8, 0.8]) - 0.5) < 1e-9
    # 30% drawdown -> liquidate
    assert e.drawdown_multiplier([1.0, 0.7]) == 0.0


def test_apply_caps_single_name():
    e = RiskEngine(max_position_pct=0.05, max_total_equity_pct=0.85)
    w = {f"s{i}": 0.2 for i in range(10)}  # 10 names x 20% = 200%
    capped = e.apply_caps(w)
    assert all(v <= 0.05 + 1e-9 for v in capped.values())
    assert abs(sum(capped.values()) - 0.5) < 1e-9  # 10 x 5%


def test_apply_caps_industry():
    e = RiskEngine(max_position_pct=0.1, max_industry_pct=0.15, max_total_equity_pct=1.0)
    w = {"a": 0.1, "b": 0.1, "c": 0.1}
    industry = {"a": "tech", "b": "tech", "c": "fin"}
    capped = e.apply_caps(w, industry=industry)
    assert abs(capped["a"] + capped["b"] - 0.15) < 1e-9


def test_size_position():
    e = RiskEngine(risk_per_trade=0.01, max_position_pct=0.05, lot_size=100)
    s = e.size_position(100000, 10.0, 9.0)
    assert s["shares"] == 500
    assert s["lots"] == 5
    assert abs(s["position_pct"] - 0.05) < 1e-9


def test_vol_multiplier_reduces_exposure():
    e = RiskEngine(target_annual_vol=0.15)
    assert e.vol_multiplier([0.05, -0.05, 0.04, -0.04] * 20) < 1.0
    assert e.vol_multiplier([0.0, 0.0]) == 1.0
