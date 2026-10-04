"""Combine per-symbol backtest curves into a portfolio equity series."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from portfolio.risk_engine import RiskEngine


class PortfolioEngine:
    def __init__(
        self,
        backtest_fn: Callable[..., Dict[str, Any]],
        risk_engine: Optional[RiskEngine] = None,
    ) -> None:
        self._backtest_fn = backtest_fn
        self._risk_engine = risk_engine

    def run_backtest(
        self,
        symbols: List[str],
        *,
        weight_mode: str = "equal",
        strategy: str = "default",
        horizon: int = 5,
        test_size: float = 0.2,
        up_threshold: float = 0.02,
        min_confidence: float = 0.0,
        max_symbols: int = 10,
    ) -> Dict[str, Any]:
        symbols = [str(s).strip() for s in symbols if str(s).strip()][:max_symbols]
        if len(symbols) < 1:
            raise ValueError("At least one symbol is required for portfolio backtest")

        per_symbol: Dict[str, Dict[str, Any]] = {}
        min_len: Optional[int] = None

        def _run_one(symbol: str) -> tuple[str, Dict[str, Any]]:
            result = self._backtest_fn(
                symbol,
                strategy=strategy,
                horizon=horizon,
                test_size=test_size,
                up_threshold=up_threshold,
                min_confidence=min_confidence,
            )
            return symbol, result

        backtest_results: Dict[str, Dict[str, Any]] = {}
        max_workers = min(4, len(symbols))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_run_one, sym) for sym in symbols]
            for fut in as_completed(futures):
                sym, result = fut.result()
                backtest_results[sym] = result

        for symbol in symbols:
            result = backtest_results.get(symbol, {})
            pnl = result.get("pnl_backtest") or {}
            strat_curve = pnl.get("equity_curve") or []
            bh_curve = pnl.get("buy_hold_curve") or []
            if len(strat_curve) < 2 or len(bh_curve) < 2:
                per_symbol[symbol] = {
                    "skipped": True,
                    "reason": "insufficient_pnl_curve",
                }
                continue

            strat_rets = []
            bh_rets = []
            for i in range(1, len(strat_curve)):
                prev_s = float(strat_curve[i - 1]) or 1.0
                prev_b = float(bh_curve[i - 1]) or 1.0
                strat_rets.append(float(strat_curve[i]) / prev_s - 1.0)
                bh_rets.append(float(bh_curve[i]) / prev_b - 1.0)

            n = min(len(strat_rets), len(bh_rets))
            strat_rets = strat_rets[:n]
            bh_rets = bh_rets[:n]
            min_len = n if min_len is None else min(min_len, n)

            per_symbol[symbol] = {
                "skipped": False,
                "strategy_return": float(pnl.get("total_return", 0)),
                "buy_hold_return": float(pnl.get("buy_hold_return", 0)),
                "excess_return": float(pnl.get("excess_return", 0)),
                "strategy_returns": strat_rets,
                "buy_hold_returns": bh_rets,
                "ensemble_accuracy": float((result.get("results") or {}).get("ensemble", {}).get("accuracy", 0)),
            }

        active = [s for s in symbols if not per_symbol.get(s, {}).get("skipped")]
        if not active or min_len is None or min_len < 1:
            raise ValueError("No valid symbol backtests for portfolio aggregation")

        weights = self._compute_weights(active, per_symbol, weight_mode)
        if self._risk_engine is not None:
            weights = self._risk_engine.apply_caps(weights)
            weights = {s: weights.get(s, 0.0) for s in active}

        port_rets = []
        bh_port_rets = []
        for day in range(min_len):
            pr = 0.0
            br = 0.0
            for sym in active:
                w = weights.get(sym, 0.0)
                pr += w * per_symbol[sym]["strategy_returns"][day]
                br += w * per_symbol[sym]["buy_hold_returns"][day]
            port_rets.append(pr)
            bh_port_rets.append(br)

        port_equity = self._curve_from_returns(port_rets)
        bh_equity = self._curve_from_returns(bh_port_rets)

        return {
            "symbols": symbols,
            "active_symbols": active,
            "weight_mode": weight_mode,
            "weights": weights,
            "horizon": horizon,
            "test_size": test_size,
            "up_threshold": up_threshold,
            "strategy": strategy,
            "per_symbol": {
                sym: {k: v for k, v in data.items() if k not in ("strategy_returns", "buy_hold_returns")}
                for sym, data in per_symbol.items()
            },
            "portfolio_return": float(port_equity[-1] - 1.0) if port_equity else 0.0,
            "buy_hold_return": float(bh_equity[-1] - 1.0) if bh_equity else 0.0,
            "excess_return": float((port_equity[-1] if port_equity else 1) - (bh_equity[-1] if bh_equity else 1)),
            "equity_curve": port_equity,
            "buy_hold_curve": bh_equity,
            "days": min_len,
        }

    def _compute_weights(
        self,
        symbols: List[str],
        per_symbol: Dict[str, Dict[str, Any]],
        weight_mode: str,
    ) -> Dict[str, float]:
        if weight_mode == "signal":
            raw = {}
            for sym in symbols:
                acc = float(per_symbol[sym].get("ensemble_accuracy", 0.5))
                raw[sym] = max(0.05, acc)
            total = sum(raw.values()) or 1.0
            return {sym: raw[sym] / total for sym in symbols}

        w = 1.0 / len(symbols)
        return {sym: w for sym in symbols}

    @staticmethod
    def _curve_from_returns(daily_returns: List[float]) -> List[float]:
        eq = 1.0
        curve = [1.0]
        for r in daily_returns:
            eq *= 1.0 + float(r)
            curve.append(round(eq, 6))
        return curve
