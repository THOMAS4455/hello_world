"""Virtual paper-trading account for digital-twin simulation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .constraints import TradingConstraints


@dataclass
class PaperPosition:
    symbol: str
    shares: int
    avg_cost: float

    def market_value(self, price: float) -> float:
        return self.shares * price


@dataclass
class PaperTrade:
    date: str
    symbol: str
    side: str
    shares: int
    price: float
    commission: float
    notional: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "symbol": self.symbol,
            "side": self.side,
            "shares": self.shares,
            "price": self.price,
            "commission": self.commission,
            "notional": self.notional,
        }


@dataclass
class PaperAccountState:
    user_id: int
    initial_capital: float = 100_000.0
    cash: float = 100_000.0
    day_index: int = 0
    last_date: str = ""
    replay_start_date: str = ""
    replay_cursor: int = 0
    positions: Dict[str, PaperPosition] = field(default_factory=dict)
    trades: List[PaperTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    equity_dates: List[str] = field(default_factory=list)
    constraints: TradingConstraints = field(default_factory=TradingConstraints)
    bought_today: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "initial_capital": self.initial_capital,
            "cash": round(self.cash, 2),
            "day_index": self.day_index,
            "last_date": self.last_date,
            "replay_start_date": self.replay_start_date,
            "replay_cursor": self.replay_cursor,
            "positions": {
                sym: {"symbol": p.symbol, "shares": p.shares, "avg_cost": p.avg_cost}
                for sym, p in self.positions.items()
            },
            "trades": [t.to_dict() for t in self.trades[-200:]],
            "equity_curve": self.equity_curve,
            "equity_dates": self.equity_dates,
            "constraints_note": self.constraints.note(),
            "constraints": {
                "max_position_pct": self.constraints.max_position_pct,
                "max_total_equity_pct": self.constraints.max_total_equity_pct,
                "enable_t_plus_one": self.constraints.enable_t_plus_one,
                "enable_limit_up_down": self.constraints.enable_limit_up_down,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperAccountState":
        positions = {}
        for sym, p in (data.get("positions") or {}).items():
            positions[sym] = PaperPosition(
                symbol=p.get("symbol", sym),
                shares=int(p.get("shares", 0)),
                avg_cost=float(p.get("avg_cost", 0)),
            )
        trades = [
            PaperTrade(
                date=t.get("date", ""),
                symbol=t.get("symbol", ""),
                side=t.get("side", ""),
                shares=int(t.get("shares", 0)),
                price=float(t.get("price", 0)),
                commission=float(t.get("commission", 0)),
                notional=float(t.get("notional", 0)),
            )
            for t in (data.get("trades") or [])
        ]
        cdata = data.get("constraints") or {}
        constraints = TradingConstraints(
            max_position_pct=float(cdata.get("max_position_pct", 0.25)),
            max_total_equity_pct=float(cdata.get("max_total_equity_pct", 0.85)),
            enable_t_plus_one=bool(cdata.get("enable_t_plus_one", True)),
            enable_limit_up_down=bool(cdata.get("enable_limit_up_down", True)),
        )
        return cls(
            user_id=int(data.get("user_id", 0)),
            initial_capital=float(data.get("initial_capital", 100_000)),
            cash=float(data.get("cash", 100_000)),
            day_index=int(data.get("day_index", 0)),
            last_date=str(data.get("last_date", "")),
            replay_start_date=str(data.get("replay_start_date", "")),
            replay_cursor=int(data.get("replay_cursor", 0)),
            positions=positions,
            trades=trades,
            equity_curve=list(data.get("equity_curve") or []),
            equity_dates=list(data.get("equity_dates") or []),
            constraints=constraints,
        )


class PaperAccount:
    def __init__(self, state: PaperAccountState) -> None:
        self.state = state

    def equity(self, prices: Dict[str, float]) -> float:
        total = self.state.cash
        for sym, pos in self.state.positions.items():
            price = float(prices.get(sym, pos.avg_cost))
            total += pos.market_value(price)
        return total

    def advance_day(
        self,
        trade_date: str,
        prices: Dict[str, float],
        target_weights: Dict[str, float],
        prev_closes: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Rebalance toward target_weights (symbol -> 0..1, sum <= max_total_equity_pct)."""
        st = self.state
        c = st.constraints
        prev_closes = prev_closes or {}
        if st.last_date != trade_date:
            st.bought_today = set()
        eq = self.equity(prices)
        st.day_index += 1
        st.replay_cursor += 1

        # Drawdown circuit breaker (deterministic, uses realized equity — no lookahead).
        from portfolio.risk_engine import RiskEngine

        dd_mult = RiskEngine().drawdown_multiplier(st.equity_curve)
        if dd_mult < 1.0:
            target_weights = {s: float(w) * dd_mult for s, w in target_weights.items()}

        for sym, pos in list(st.positions.items()):
            price = float(prices.get(sym, 0))
            if price <= 0:
                continue
            if not c.can_sell(sym, st.bought_today):
                continue
            prev_close = float(prev_closes.get(sym, price))
            if not c.can_trade("sell", sym, price, prev_close):
                continue
            target_w = float(target_weights.get(sym, 0.0))
            target_value = eq * min(target_w, c.max_position_pct)
            current_value = pos.market_value(price)
            if target_value >= current_value - 1e-6:
                continue
            sell_value = current_value - target_value
            sell_shares = c.round_lots(sell_value / price)
            sell_shares = min(sell_shares, pos.shares)
            if sell_shares <= 0:
                continue
            notional = sell_shares * price
            comm = c.cost("sell", notional)
            st.cash += notional - comm
            pos.shares -= sell_shares
            if pos.shares <= 0:
                del st.positions[sym]
            st.trades.append(
                PaperTrade(trade_date, sym, "sell", sell_shares, price, comm, notional)
            )

        eq = self.equity(prices)
        for sym, weight in target_weights.items():
            weight = float(weight)
            if weight <= 0:
                continue
            price = float(prices.get(sym, 0))
            if price <= 0:
                continue
            prev_close = float(prev_closes.get(sym, price))
            if not c.can_trade("buy", sym, price, prev_close):
                continue
            target_value = eq * min(weight, c.max_position_pct)
            pos = st.positions.get(sym)
            current_value = pos.market_value(price) if pos else 0.0
            if target_value <= current_value + 1e-6:
                continue
            buy_value = target_value - current_value
            buy_shares = c.round_lots(buy_value / price)
            if buy_shares <= 0:
                continue
            notional = buy_shares * price
            comm = c.cost("buy", notional)
            total_cost = notional + comm
            if total_cost > st.cash:
                affordable = c.round_lots((st.cash - c.min_commission) / price)
                if affordable <= 0:
                    continue
                buy_shares = affordable
                notional = buy_shares * price
                comm = c.cost("buy", notional)
                total_cost = notional + comm
            st.cash -= total_cost
            if pos:
                total_shares = pos.shares + buy_shares
                pos.avg_cost = (pos.avg_cost * pos.shares + price * buy_shares) / total_shares
                pos.shares = total_shares
            else:
                st.positions[sym] = PaperPosition(sym, buy_shares, price)
            st.bought_today.add(sym)
            st.trades.append(
                PaperTrade(trade_date, sym, "buy", buy_shares, price, comm, notional)
            )

        eq_end = self.equity(prices)
        st.equity_curve.append(round(eq_end, 2))
        st.equity_dates.append(trade_date)
        st.last_date = trade_date
        return {
            "date": trade_date,
            "equity": eq_end,
            "cash": st.cash,
            "positions": deepcopy(st.positions),
            "trades_today": [t.to_dict() for t in st.trades if t.date == trade_date],
            "replay_cursor": st.replay_cursor,
        }
