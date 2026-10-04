"""A-share trading constraints for paper trading."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass
class TradingConstraints:
    lot_size: int = 100
    commission_rate: float = 0.00025   # 万2.5 (broker commission)
    min_commission: float = 5.0
    stamp_tax_rate: float = 0.0005      # 卖出印花税 0.05% (since 2023-08)
    transfer_fee_rate: float = 0.00001  # 过户费 0.001% (both sides)
    max_position_pct: float = 0.25
    max_total_equity_pct: float = 0.85
    enable_t_plus_one: bool = True
    enable_limit_up_down: bool = True
    limit_pct: float = 0.095

    def round_lots(self, shares: float) -> int:
        if shares < self.lot_size:
            return 0
        return int(shares // self.lot_size) * self.lot_size

    def commission(self, notional: float) -> float:
        return max(self.min_commission, abs(notional) * self.commission_rate)

    def cost(self, side: str, notional: float) -> float:
        """Total one-way cost (CNY) for a trade of `notional` value.

        buy  = commission + transfer fee
        sell = commission + transfer fee + stamp tax
        """
        amount = abs(float(notional))
        total = max(self.min_commission, amount * self.commission_rate) + amount * self.transfer_fee_rate
        if str(side).lower() == "sell":
            total += amount * self.stamp_tax_rate
        return total

    def cost_rate(self, side: str) -> float:
        """Per-notional one-way cost fraction (ignores the min-commission floor)."""
        rate = self.commission_rate + self.transfer_fee_rate
        if str(side).lower() == "sell":
            rate += self.stamp_tax_rate
        return rate

    def can_trade(self, side: str, symbol: str, price: float, prev_close: float) -> bool:
        if not self.enable_limit_up_down or prev_close <= 0 or price <= 0:
            return True
        change = abs(price / prev_close - 1.0)
        return change < self.limit_pct

    def can_sell(self, symbol: str, bought_today: Set[str]) -> bool:
        if not self.enable_t_plus_one:
            return True
        return symbol not in bought_today

    def note(self) -> str:
        parts = [
            f"{self.lot_size}-share lots",
            f"commission max({self.min_commission}, rate×notional)",
            "long/cash only",
        ]
        if self.enable_t_plus_one:
            parts.append("T+1 sell restriction")
        if self.enable_limit_up_down:
            parts.append(f"limit-up/down block at ±{self.limit_pct * 100:.1f}%")
        else:
            parts.append("limit-up/down not modeled")
        return "Paper simulation: " + "; ".join(parts) + "."
