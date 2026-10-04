import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from trading.constraints import TradingConstraints


def test_cost_rates_include_stamp_tax_on_sell():
    c = TradingConstraints()
    assert abs(c.cost_rate("buy") - (0.00025 + 0.00001)) < 1e-9
    assert abs(c.cost_rate("sell") - (0.00025 + 0.00001 + 0.0005)) < 1e-9


def test_cost_cny():
    c = TradingConstraints()
    # sell 100000: commission 25 + transfer 1 + stamp 50 = 76
    assert abs(c.cost("sell", 100000) - 76.0) < 1e-9
    assert abs(c.cost("buy", 100000) - 26.0) < 1e-9


def test_min_commission_floor():
    c = TradingConstraints()
    # tiny notional -> min commission 5 + transfer
    assert abs(c.cost("buy", 100) - (5.0 + 100 * c.transfer_fee_rate)) < 1e-9
