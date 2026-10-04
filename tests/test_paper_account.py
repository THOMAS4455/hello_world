"""Tests for paper trading account."""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from trading.paper_account import PaperAccount, PaperAccountState


def test_paper_account_buy_and_equity():
    state = PaperAccountState(user_id=1, initial_capital=100_000, cash=100_000)
    account = PaperAccount(state)
    prices = {"000001": 10.0}
    step = account.advance_day("2026-06-01", prices, {"000001": 0.5})
    assert step["equity"] > 0
    assert state.day_index == 1
    assert len(state.equity_curve) >= 1


def test_t_plus_one_blocks_same_day_sell():
    from trading.constraints import TradingConstraints

    state = PaperAccountState(user_id=1, initial_capital=100_000, cash=100_000)
    state.constraints = TradingConstraints(enable_t_plus_one=True)
    account = PaperAccount(state)
    prices = {"000001": 10.0}
    account.advance_day("2026-06-01", prices, {"000001": 0.5})
    shares_before = state.positions.get("000001").shares if "000001" in state.positions else 0
    account.advance_day("2026-06-01", prices, {"000001": 0.0})
    shares_after = state.positions.get("000001").shares if "000001" in state.positions else 0
    assert shares_after == shares_before
