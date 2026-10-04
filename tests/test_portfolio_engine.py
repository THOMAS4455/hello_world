"""Tests for portfolio engine aggregation."""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from portfolio.portfolio_engine import PortfolioEngine


def _fake_backtest(symbol, **kwargs):
  n = 10
  strat = [1.0]
  bh = [1.0]
  for i in range(n):
    strat.append(strat[-1] * (1.0 + (0.01 if symbol == "A" else -0.005)))
    bh.append(bh[-1] * (1.0 + 0.002))
  return {
    "results": {"ensemble": {"accuracy": 0.7 if symbol == "A" else 0.55}},
    "pnl_backtest": {
      "total_return": strat[-1] - 1,
      "buy_hold_return": bh[-1] - 1,
      "excess_return": (strat[-1] - bh[-1]),
      "equity_curve": strat,
      "buy_hold_curve": bh,
    },
  }


def test_portfolio_engine_equal_weight():
  engine = PortfolioEngine(_fake_backtest)
  result = engine.run_backtest(["A", "B"], weight_mode="equal", max_symbols=10)
  assert len(result["equity_curve"]) == len(result["buy_hold_curve"])
  assert result["active_symbols"] == ["A", "B"]
  assert abs(sum(result["weights"].values()) - 1.0) < 1e-6
