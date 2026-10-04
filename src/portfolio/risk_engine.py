"""Portfolio risk controls: drawdown circuit breaker, volatility targeting,
concentration caps, and fixed-fractional position sizing.

This module is deterministic and does not depend on any prediction signal — it
is the one part of the system whose value does not rest on forecasting skill.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np


class RiskEngine:
    def __init__(
        self,
        *,
        max_drawdown: float = 0.15,
        max_drawdown_critical: float = 0.25,
        target_annual_vol: float = 0.15,
        max_position_pct: float = 0.05,
        max_industry_pct: float = 0.20,
        max_total_equity_pct: float = 0.85,
        risk_per_trade: float = 0.01,
        lot_size: int = 100,
    ) -> None:
        self.max_drawdown = float(max_drawdown)
        self.max_drawdown_critical = float(max_drawdown_critical)
        self.target_annual_vol = float(target_annual_vol)
        self.max_position_pct = float(max_position_pct)
        self.max_industry_pct = float(max_industry_pct)
        self.max_total_equity_pct = float(max_total_equity_pct)
        self.risk_per_trade = float(risk_per_trade)
        self.lot_size = int(lot_size)

    # ------------------------------------------------------------------
    # Drawdown circuit breaker
    # ------------------------------------------------------------------
    @staticmethod
    def drawdown(equity: Sequence[float]) -> float:
        peak = -np.inf
        mdd = 0.0
        for v in equity:
            peak = max(peak, float(v))
            if peak > 0:
                mdd = max(mdd, (peak - float(v)) / peak)
        return float(mdd)

    def drawdown_multiplier(self, equity: Sequence[float]) -> float:
        """Return a 0..1 target-exposure multiplier from the current drawdown."""
        dd = self.drawdown(equity)
        if dd >= self.max_drawdown_critical:
            return 0.0
        if dd <= self.max_drawdown:
            return 1.0
        span = self.max_drawdown_critical - self.max_drawdown
        return float((self.max_drawdown_critical - dd) / span if span > 0 else 0.0)

    # ------------------------------------------------------------------
    # Volatility targeting
    # ------------------------------------------------------------------
    @staticmethod
    def realized_vol(returns: Sequence[float], periods_per_year: int = 252) -> float:
        arr = np.asarray(returns, dtype=float)
        if len(arr) < 2:
            return 0.0
        return float(np.std(arr, ddof=1) * np.sqrt(periods_per_year))

    def vol_multiplier(self, returns: Sequence[float]) -> float:
        rv = self.realized_vol(returns)
        if rv <= 1e-9:
            return 1.0
        return float(np.clip(self.target_annual_vol / rv, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Concentration caps
    # ------------------------------------------------------------------
    def apply_caps(
        self,
        weights: Dict[str, float],
        industry: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """Clip single-name and industry weights, then scale total exposure."""
        out = {k: max(0.0, float(v)) for k, v in weights.items() if float(v) > 0}
        if not out:
            return {}

        # single-name cap
        for k in out:
            out[k] = min(out[k], self.max_position_pct)

        # industry cap
        if industry:
            groups: Dict[str, List[str]] = {}
            for k in out:
                groups.setdefault(str(industry.get(k) or "other"), []).append(k)
            for _, members in groups.items():
                total = sum(out[m] for m in members)
                if total > self.max_industry_pct:
                    scale = self.max_industry_pct / total if total > 0 else 1.0
                    for m in members:
                        out[m] *= scale

        # total exposure cap
        total = sum(out.values())
        if total > self.max_total_equity_pct:
            scale = self.max_total_equity_pct / total if total > 0 else 1.0
            out = {k: v * scale for k, v in out.items()}

        return out

    # ------------------------------------------------------------------
    # Fixed-fractional position sizing
    # ------------------------------------------------------------------
    def size_position(
        self,
        capital: float,
        entry_price: float,
        stop_price: float,
        max_position_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Size a single position by risking `risk_per_trade` of capital."""
        capital = float(capital)
        entry = float(entry_price)
        stop = float(stop_price)
        cap_pct = self.max_position_pct if max_position_pct is None else float(max_position_pct)

        risk_per_share = max(entry - stop, 0.01)
        risk_budget = capital * self.risk_per_trade
        shares = int(risk_budget / risk_per_share)
        max_shares = int(capital * cap_pct / entry) if entry > 0 else 0
        shares = min(shares, max_shares)
        lots = shares // self.lot_size
        shares = lots * self.lot_size

        return {
            "shares": shares,
            "lots": lots,
            "position_pct": round(shares * entry / capital, 4) if capital > 0 else 0.0,
            "notional": round(shares * entry, 2),
            "risk_per_share": round(risk_per_share, 4),
            "risk_budget": round(risk_budget, 2),
        }

    # ------------------------------------------------------------------
    # Composite
    # ------------------------------------------------------------------
    def scale_weights(
        self,
        weights: Dict[str, float],
        *,
        equity: Optional[Sequence[float]] = None,
        returns: Optional[Sequence[float]] = None,
        industry: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """Apply caps, then drawdown circuit breaker, then vol targeting."""
        out = self.apply_caps(weights, industry=industry)
        if equity is not None and len(equity) > 0:
            mult = self.drawdown_multiplier(equity)
            out = {k: v * mult for k, v in out.items()}
        if returns is not None and len(returns) > 1:
            mult = self.vol_multiplier(returns)
            out = {k: v * mult for k, v in out.items()}
        return out
