"""
Investment workspace: watchlist, portfolio backtest, paper trading, signal stats, daily brief.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from copy import deepcopy
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from portfolio.portfolio_engine import PortfolioEngine
from portfolio.portfolio_metrics import compare_strategies, compute_metrics
from portfolio.risk_engine import RiskEngine
from trading.constraints import TradingConstraints
from trading.paper_account import PaperAccount, PaperAccountState
from validation.meta_label_filter import compute_meta_score, filter_target_weights
from validation.outcome_resolver import OutcomeResolver
from validation.signal_tracker import SignalTracker
from research.decision_engine import analyze_holding, build_candidate_report, build_entry_plan
from research import screener_config as SC

from flask_services.investment_repository import JsonInvestmentRepository


DEFAULT_CONFIG = {
    "risk_level": "balanced",
    "weight_mode": "equal",
    "max_position_pct": 0.25,
    "max_total_equity_pct": 0.85,
    "horizon": 5,
    "up_threshold": 0.02,
    "min_confidence": 0.0,
    "initial_capital": 100_000.0,
    "label_mode": "fixed_horizon",
    "auto_advance_paper": False,
    "max_symbols": 10,
}

RISK_LEVEL_MAP = {
    "conservative": {
        "min_confidence": 0.65,
        "max_total_equity_pct": 0.60,
        "max_position_pct": 0.15,
        "weight_mode": "equal",
    },
    "balanced": {
        "min_confidence": 0.0,
        "max_total_equity_pct": 0.85,
        "max_position_pct": 0.25,
        "weight_mode": "equal",
    },
    "aggressive": {
        "min_confidence": 0.45,
        "max_total_equity_pct": 0.95,
        "max_position_pct": 0.35,
        "weight_mode": "signal",
    },
}


class InvestmentService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        data_dir = Path(__file__).parent.parent / "data"
        self._repo = JsonInvestmentRepository(data_dir)
        self.signal_tracker = SignalTracker(data_dir / "signal_logs.json")
        self._portfolio_cache: Dict[str, Dict[str, Any]] = {}
        self._portfolio_cache_ttl = 3600
        self._prediction_service = None
        self._outcome_resolver: Optional[OutcomeResolver] = None

    def _get_prediction_service(self):
        if self._prediction_service is None:
            from flask_services.prediction_service import prediction_service

            self._prediction_service = prediction_service
        return self._prediction_service

    def _get_outcome_resolver(self) -> OutcomeResolver:
        if self._outcome_resolver is None:
            pred_svc = self._get_prediction_service()
            self._outcome_resolver = OutcomeResolver(
                self.signal_tracker,
                price_loader=pred_svc._load_history_df,
            )
        return self._outcome_resolver

    def _resolve_signals_lazy(self, label_mode: Optional[str] = None) -> int:
        try:
            mode = label_mode or "fixed_horizon"
            return self._get_outcome_resolver().resolve_pending(label_mode=mode)
        except Exception:
            return 0

    @staticmethod
    def _effective_config(config: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(DEFAULT_CONFIG)
        merged.update(config or {})
        level = str(merged.get("risk_level", "balanced"))
        merged.update(RISK_LEVEL_MAP.get(level, RISK_LEVEL_MAP["balanced"]))
        passthrough = (
            "horizon",
            "up_threshold",
            "initial_capital",
            "label_mode",
            "auto_advance_paper",
            "max_symbols",
            "weight_mode",
        )
        for key in passthrough:
            if key in (config or {}):
                merged[key] = config[key]
        return merged

    @staticmethod
    def _constraints_from_config(config: Dict[str, Any]) -> TradingConstraints:
        cfg = InvestmentService._effective_config(config)
        return TradingConstraints(
            max_position_pct=float(cfg.get("max_position_pct", 0.25)),
            max_total_equity_pct=float(cfg.get("max_total_equity_pct", 0.85)),
            enable_t_plus_one=True,
            enable_limit_up_down=True,
        )

    def _load_investments(self) -> Dict[str, Any]:
        return self._repo.load_investments()

    def _save_investments(self, payload: Dict[str, Any]) -> None:
        self._repo.save_investments(payload)

    def _load_paper(self) -> Dict[str, Any]:
        return self._repo.load_paper()

    def _save_paper(self, payload: Dict[str, Any]) -> None:
        self._repo.save_paper(payload)

    def _user_bucket(self, user_id: int) -> Dict[str, Any]:
        payload = self._load_investments()
        by_user = payload.setdefault("by_user", {})
        key = str(user_id)
        if key not in by_user:
            by_user[key] = {
                "watchlist": [],
                "config": deepcopy(DEFAULT_CONFIG),
                "updated_at": datetime.now().isoformat(),
            }
        return by_user[key]

    def get_watchlist(self, user_id: int) -> Dict[str, Any]:
        with self._lock:
            bucket = self._user_bucket(user_id)
            return {
                "symbols": list(bucket.get("watchlist") or []),
                "config": self._effective_config(bucket.get("config") or DEFAULT_CONFIG),
                "updated_at": bucket.get("updated_at"),
            }

    def update_watchlist(self, user_id: int, symbols: List[str]) -> Dict[str, Any]:
        cleaned = []
        seen = set()
        for s in symbols:
            sym = str(s).strip()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            cleaned.append(sym)
            if len(cleaned) >= 20:
                break
        with self._lock:
            payload = self._load_investments()
            bucket = self._user_bucket(user_id)
            bucket["watchlist"] = cleaned
            bucket["updated_at"] = datetime.now().isoformat()
            payload["by_user"][str(user_id)] = bucket
            self._save_investments(payload)
            return self.get_watchlist(user_id)

    def get_portfolio_config(self, user_id: int) -> Dict[str, Any]:
        with self._lock:
            bucket = self._user_bucket(user_id)
            return self._effective_config(bucket.get("config") or DEFAULT_CONFIG)

    def update_portfolio_config(self, user_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        allowed = set(DEFAULT_CONFIG.keys())
        with self._lock:
            bucket = self._user_bucket(user_id)
            stored = deepcopy(bucket.get("config") or DEFAULT_CONFIG)
            for key, value in (config or {}).items():
                if key in allowed:
                    stored[key] = value
            bucket["config"] = stored
            bucket["updated_at"] = datetime.now().isoformat()
            payload = self._load_investments()
            payload["by_user"][str(user_id)] = bucket
            self._save_investments(payload)
            return self._effective_config(stored)

    def run_portfolio_backtest(
        self,
        user_id: int,
        symbols: Optional[List[str]] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        watch = self.get_watchlist(user_id)
        config = watch.get("config") or DEFAULT_CONFIG
        syms = symbols or watch.get("symbols") or []
        if not syms:
            raise ValueError("Watchlist is empty. Add symbols first.")

        weight_mode = str(params.get("weight_mode") or config.get("weight_mode", "equal"))
        horizon = int(params.get("horizon") or config.get("horizon", 5))
        test_size = float(params.get("test_size") or 0.2)
        up_threshold = float(params.get("up_threshold") or config.get("up_threshold", 0.02))
        min_confidence = float(params.get("min_confidence") or config.get("min_confidence", 0.0))
        strategy = str(params.get("strategy") or "default")
        max_symbols = int(params.get("max_symbols") or config.get("max_symbols", 10))

        cache_key = json.dumps(
            {
                "user_id": user_id,
                "symbols": syms,
                "weight_mode": weight_mode,
                "horizon": horizon,
                "test_size": test_size,
                "up_threshold": up_threshold,
                "min_confidence": min_confidence,
                "strategy": strategy,
                "max_symbols": max_symbols,
            },
            sort_keys=True,
        )
        cached = self._portfolio_cache.get(cache_key)
        if cached and (time.time() - cached["ts"]) < self._portfolio_cache_ttl:
            return cached["data"]

        pred_svc = self._get_prediction_service()
        engine = PortfolioEngine(pred_svc.backtest_strategy, risk_engine=RiskEngine())
        result = engine.run_backtest(
            syms,
            weight_mode=weight_mode,
            strategy=strategy,
            horizon=horizon,
            test_size=test_size,
            up_threshold=up_threshold,
            min_confidence=min_confidence,
            max_symbols=max_symbols,
        )
        result["metrics"] = compare_strategies(
            result.get("equity_curve") or [],
            result.get("buy_hold_curve") or [],
        )
        result["cache_key"] = cache_key
        result["user_id"] = user_id
        result["timestamp"] = time.time()
        result["truncated_symbols"] = syms[max_symbols:] if len(syms) > max_symbols else []
        self._portfolio_cache[cache_key] = {"ts": time.time(), "data": result}
        return result

    def get_portfolio_report(self, cache_key: str) -> Optional[Dict[str, Any]]:
        cached = self._portfolio_cache.get(cache_key)
        if cached and (time.time() - cached["ts"]) < self._portfolio_cache_ttl:
            return cached["data"]
        return None

    def get_paper_account(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            payload = self._load_paper()
            raw = (payload.get("by_user") or {}).get(str(user_id))
            if not raw:
                return None
            return PaperAccountState.from_dict(raw).to_dict()

    def create_paper_account(self, user_id: int, initial_capital: Optional[float] = None) -> Dict[str, Any]:
        config = self.get_portfolio_config(user_id)
        capital = float(initial_capital or config.get("initial_capital", 100_000))
        state = PaperAccountState(user_id=user_id, initial_capital=capital, cash=capital)
        state.constraints = self._constraints_from_config(config)
        state.equity_curve = [capital]
        state.equity_dates = []
        state.replay_cursor = 0
        with self._lock:
            payload = self._load_paper()
            payload.setdefault("by_user", {})[str(user_id)] = state.to_dict()
            self._save_paper(payload)
            return state.to_dict()

    @staticmethod
    def _trade_date_to_ts(trade_date: str) -> float:
        try:
            dt = datetime.strptime(str(trade_date)[:10], "%Y-%m-%d")
            return datetime.combine(dt.date(), dt_time(23, 59, 59)).timestamp()
        except Exception:
            return time.time()

    def _price_on_date(self, pred_svc: Any, symbol: str, trade_date: str) -> Tuple[Optional[float], Optional[float]]:
        sdf = pred_svc._load_history_df(symbol)
        if "date" not in sdf.columns:
            return None, None
        work = sdf.copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        target = pd.to_datetime(str(trade_date)[:10], errors="coerce")
        if pd.isna(target):
            return None, None
        eligible = work[work["date"] <= target].sort_values("date")
        if eligible.empty:
            return None, None
        row = eligible.iloc[-1]
        price = float(row["close_price"])
        prev = float(eligible.iloc[-2]["close_price"]) if len(eligible) > 1 else price
        return price, prev

    def _replay_trading_day(
        self,
        symbols: List[str],
        cursor: int,
    ) -> Tuple[str, Dict[str, float], Dict[str, float], int, int]:
        pred_svc = self._get_prediction_service()
        ref_sym = symbols[0]
        df = pred_svc._load_history_df(ref_sym)
        if "date" not in df.columns:
            raise ValueError("Historical data missing date column for replay.")

        dates = pd.to_datetime(df["date"], errors="coerce").dropna().sort_values().astype(str).str[:10].tolist()
        test_start = max(0, int(len(dates) * 0.8))
        idx = test_start + cursor
        if idx >= len(dates):
            raise ValueError("Replay finished: no more trading days in test window.")

        trade_date = str(dates[idx])
        prices: Dict[str, float] = {}
        prev_closes: Dict[str, float] = {}
        for sym in symbols:
            price, prev = self._price_on_date(pred_svc, sym, trade_date)
            if price is None:
                continue
            prices[sym] = price
            prev_closes[sym] = prev if prev is not None else price

        remaining = len(dates) - idx - 1
        return trade_date, prices, prev_closes, idx, remaining

    def advance_paper_day(self, user_id: int) -> Dict[str, Any]:
        watch = self.get_watchlist(user_id)
        symbols = watch.get("symbols") or []
        if not symbols:
            raise ValueError("Watchlist is empty.")

        config = self._effective_config(watch.get("config") or DEFAULT_CONFIG)
        max_symbols = int(config.get("max_symbols", 10))
        active_symbols = symbols[:max_symbols]

        with self._lock:
            payload = self._load_paper()
            raw = (payload.get("by_user") or {}).get(str(user_id))
            if not raw:
                raise ValueError("Paper account not found. Create one first.")
            state = PaperAccountState.from_dict(raw)

        state.constraints = self._constraints_from_config(config)
        pred_svc = self._get_prediction_service()
        horizon = int(config.get("horizon", 5))
        up_threshold = float(config.get("up_threshold", 0.02))
        min_confidence = float(config.get("min_confidence", 0.0))
        weight_mode = str(config.get("weight_mode", "equal"))

        trade_date, prices, prev_closes, _, remaining = self._replay_trading_day(
            active_symbols, state.replay_cursor
        )

        cutoff_ts = self._trade_date_to_ts(trade_date)
        signals: Dict[str, Dict[str, Any]] = {}
        for sym in active_symbols:
            if sym not in prices:
                continue
            try:
                pred = pred_svc.predict_stock(
                    sym,
                    horizon=horizon,
                    up_threshold=up_threshold,
                    as_of_date=trade_date,
                    record_signal=False,
                )
                signals[sym] = pred
            except Exception:
                continue

        target_weights = self._target_weights_from_signals(
            symbols=list(prices.keys()),
            signals=signals,
            weight_mode=weight_mode,
            min_confidence=min_confidence,
            max_total=float(config.get("max_total_equity_pct", 0.85)),
        )

        self._resolve_signals_lazy(config.get("label_mode"))
        with self.signal_tracker._lock:
            payload_logs = self.signal_tracker._load().get("logs", [])
        resolved_logs = [
            x for x in payload_logs
            if x.get("outcome_resolved") and float(x.get("recorded_at", 0)) <= cutoff_ts
        ]
        target_weights = filter_target_weights(
            target_weights, signals, resolved_logs, cutoff_ts=cutoff_ts
        )

        account = PaperAccount(state)
        step = account.advance_day(trade_date, prices, target_weights, prev_closes=prev_closes)

        with self._lock:
            payload = self._load_paper()
            payload.setdefault("by_user", {})[str(user_id)] = account.state.to_dict()
            self._save_paper(payload)

        return {
            "step": step,
            "account": account.state.to_dict(),
            "target_weights": target_weights,
            "prices": prices,
            "replay_remaining_days": remaining,
            "signals": {
                sym: {
                    "direction": s.get("direction"),
                    "confidence": s.get("confidence"),
                    "prediction": s.get("prediction"),
                    "meta": compute_meta_score(
                        symbol=sym,
                        prediction=int(s.get("prediction", 0)),
                        confidence=float(s.get("confidence") or 0),
                        resolved_logs=resolved_logs,
                        cutoff_ts=cutoff_ts,
                    ),
                }
                for sym, s in signals.items()
            },
            "trade_date": trade_date,
            "point_in_time": True,
        }

    def get_paper_equity_curve(self, user_id: int) -> Dict[str, Any]:
        acct = self.get_paper_account(user_id)
        if not acct:
            return {"equity_curve": [], "equity_dates": [], "initial_capital": 0}
        curve = acct.get("equity_curve") or []
        metrics = compute_metrics(curve) if len(curve) >= 2 else {}
        return {
            "equity_curve": curve,
            "equity_dates": acct.get("equity_dates") or [],
            "initial_capital": acct.get("initial_capital", 0),
            "replay_cursor": acct.get("replay_cursor", 0),
            "metrics": metrics,
        }

    def get_paper_trades(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        acct = self.get_paper_account(user_id)
        if not acct:
            return []
        trades = acct.get("trades") or []
        return trades[-limit:]

    def get_signal_stats(
        self,
        symbol: str,
        limit: int = 50,
        label_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        mode = label_mode or DEFAULT_CONFIG.get("label_mode", "fixed_horizon")
        self._resolve_signals_lazy(mode)
        stats = self.signal_tracker.get_stats(symbol, limit=limit)
        with self.signal_tracker._lock:
            logs = self.signal_tracker._load().get("logs", [])
        resolved = [x for x in logs if x.get("outcome_resolved")]
        if stats.get("samples", 0) > 0:
            latest = [x for x in resolved if str(x.get("symbol")) == symbol.strip()][:1]
            if latest:
                stats["meta"] = compute_meta_score(
                    symbol=symbol,
                    prediction=int(latest[0].get("prediction", 0)),
                    confidence=float(latest[0].get("confidence") or 0),
                    resolved_logs=resolved,
                )
        return stats

    def get_daily_brief(self, user_id: int) -> Dict[str, Any]:
        watch = self.get_watchlist(user_id)
        symbols = watch.get("symbols") or []
        config = self._effective_config(watch.get("config") or DEFAULT_CONFIG)
        pred_svc = self._get_prediction_service()
        horizon = int(config.get("horizon", 5))
        up_threshold = float(config.get("up_threshold", 0.02))

        self._resolve_signals_lazy(config.get("label_mode"))
        with self.signal_tracker._lock:
            logs = self.signal_tracker._load().get("logs", [])
        resolved_logs = [x for x in logs if x.get("outcome_resolved")]

        snapshots = []
        low_confidence = []
        filtered_signals = []
        bullish = 0
        bearish = 0

        for sym in symbols[:15]:
            try:
                pred = pred_svc.predict_stock(sym, horizon=horizon, up_threshold=up_threshold)
                conf = float(pred.get("confidence") or 0)
                direction = pred.get("direction", "down")
                meta = compute_meta_score(
                    symbol=sym,
                    prediction=int(pred.get("prediction", 0)),
                    confidence=conf,
                    resolved_logs=resolved_logs,
                )
                stats = self.signal_tracker.get_stats(sym, limit=20)
                if direction == "up":
                    bullish += 1
                else:
                    bearish += 1
                item = {
                    "symbol": sym,
                    "direction": direction,
                    "confidence": conf,
                    "prediction": pred.get("prediction"),
                    "ensemble_up": (pred.get("layer_outputs") or {}).get("ensemble_up"),
                    "meta_score": meta["meta_score"],
                    "trade_allowed": meta["trade_allowed"],
                    "signal_stats": {
                        "accuracy": stats.get("accuracy", 0),
                        "samples": stats.get("samples", 0),
                    },
                }
                snapshots.append(item)
                filtered_signals.append({**item, "meta": meta})
                if conf < 0.55 or not meta["trade_allowed"]:
                    low_confidence.append(sym)
            except Exception as exc:
                snapshots.append({"symbol": sym, "error": str(exc)})

        paper = self.get_paper_account(user_id)
        paper_summary = None
        if paper:
            eq = paper.get("equity_curve") or []
            paper_summary = {
                "cash": paper.get("cash"),
                "positions_count": len(paper.get("positions") or {}),
                "last_equity": eq[-1] if eq else paper.get("initial_capital"),
                "day_index": paper.get("day_index", 0),
                "replay_cursor": paper.get("replay_cursor", 0),
            }

        return {
            "generated_at": datetime.now().isoformat(),
            "watchlist_size": len(symbols),
            "bullish_count": bullish,
            "bearish_count": bearish,
            "low_confidence_symbols": low_confidence,
            "snapshots": snapshots,
            "filtered_signals": filtered_signals,
            "paper_account": paper_summary,
            "label_mode": config.get("label_mode", "fixed_horizon"),
            "risk_note": (
                "Signals are research outputs only, not investment advice. "
                "Paper trading uses T+1 and simplified limit-up/down rules."
            ),
        }

    def get_holding_advice(self, holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user-entered holdings without placing orders or mutating state."""
        pred_svc = self._get_prediction_service()
        items = []
        errors = []
        for holding in holdings[:50]:
            symbol = str(holding.get("symbol") or "").strip()
            try:
                history = pred_svc._load_history_df(symbol)
                prediction = pred_svc.predict_stock(symbol, horizon=5, up_threshold=0.02, record_signal=False)
                items.append(analyze_holding(
                    symbol=symbol,
                    history=history,
                    quantity=int(holding["quantity"]),
                    available_quantity=int(holding.get("available_quantity") if holding.get("available_quantity") is not None else holding["quantity"]),
                    average_cost=float(holding["average_cost"]),
                    prediction=prediction,
                ))
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})
        return {
            "generated_at": datetime.now().isoformat(),
            "items": items,
            "errors": errors,
            "risk_note": "Research output only; T+1 availability and broker execution must be confirmed before trading.",
        }

    def run_candidate_research(self, symbols: List[str], min_score: float = 0.60, top_n: int = 10) -> Dict[str, Any]:
        """Screen a supplied, point-in-time universe using the QuantA factor core."""
        pred_svc = self._get_prediction_service()
        histories, skipped = {}, []
        for raw_symbol in symbols[:50]:
            symbol = str(raw_symbol).strip()
            try:
                histories[symbol] = pred_svc._load_history_df(symbol)
            except Exception as exc:
                skipped.append({"symbol": symbol, "error": str(exc)})
        candidates = build_candidate_report(histories, min_score=float(min_score), top_n=int(top_n))
        return {
            "generated_at": datetime.now().isoformat(),
            "coverage": {"requested": len(symbols), "loaded": len(histories), "skipped": skipped},
            "market_regime": "normal",
            "candidates": candidates,
            "risk_note": "Research output only. Full-market reports require a scheduled historical-data snapshot, not live per-symbol requests.",
        }

    def _prefilter_universe(self, stocks: List[Dict[str, Any]], max_pool: Optional[int] = None) -> List[Dict[str, Any]]:
        """Narrow the full A-share universe to a liquid, tradeable shortlist."""
        if max_pool is None:
            max_pool = SC.PRE_MAX_POOL
        pool: List[Dict[str, Any]] = []
        for item in stocks or []:
            symbol = str(item.get("symbol") or "")
            name = str(item.get("name") or "")
            price = float(item.get("price") or 0)
            market_cap = float(item.get("market_cap") or 0)
            volume = float(item.get("volume") or 0)
            if not symbol or price <= 0:
                continue
            if any(tok in name.upper() for tok in SC.PRE_EXCLUDE_NAME_TOKENS):
                continue
            if symbol[:2] not in SC.PRE_ALLOWED_PREFIXES:
                continue
            if not (SC.PRE_MIN_PRICE <= price <= SC.PRE_MAX_PRICE):
                continue
            if market_cap < SC.PRE_MIN_MARKET_CAP:
                continue
            if volume <= 0:
                continue
            change_percent = float(item.get("change_percent") or 0)
            turnover = volume / market_cap if market_cap > 0 else 0.0
            quick_score = change_percent + SC.PRE_QUICK_TURNOVER_SCALE * min(turnover, SC.PRE_QUICK_TURNOVER_CAP)
            pool.append({
                "symbol": symbol,
                "name": name,
                "price": price,
                "change_percent": change_percent,
                "volume": volume,
                "market_cap": market_cap,
                "quick_score": quick_score,
            })
        pool.sort(key=lambda x: x["quick_score"], reverse=True)
        return pool[:max_pool]

    def run_daily_screener(
        self,
        top_n: int = 5,
        capital: float = 100_000.0,
        min_confidence: float = 0.55,
    ) -> Dict[str, Any]:
        """Autonomously screen the A-share market and pick the top-N predicted-up stocks.

        Pipeline: cached full-market snapshot -> liquidity/tradability pre-filter ->
        factor screen (decision engine) -> ML direction prediction -> precise
        parameter-level entry plans -> persisted daily picks.
        """
        from flask_services.data_service import data_service

        pred_svc = self._get_prediction_service()

        snapshot = data_service.get_stocks(limit=0, force_refresh=False)
        snapshot_data = snapshot.get("data") or snapshot
        stocks = snapshot_data.get("stocks") or []

        pool = self._prefilter_universe(stocks, max_pool=SC.PRE_MAX_POOL)
        name_map = {item["symbol"]: item["name"] for item in pool}

        histories: Dict[str, Any] = {}
        skipped: List[Dict[str, Any]] = []
        for item in pool:
            symbol = item["symbol"]
            try:
                histories[symbol] = pred_svc._load_history_df(symbol)
            except Exception as exc:
                skipped.append({"symbol": symbol, "error": str(exc)})

        candidates = build_candidate_report(histories, min_score=SC.FACTOR_MIN_SCORE, top_n=SC.FACTOR_TOP_N)

        up_picks: List[Dict[str, Any]] = []
        fallback_picks: List[Dict[str, Any]] = []
        for cand in candidates:
            symbol = cand["symbol"]
            try:
                pred = pred_svc.predict_stock(symbol, horizon=5, up_threshold=0.02, record_signal=False)
            except Exception as exc:
                skipped.append({"symbol": symbol, "error": str(exc)})
                continue
            direction = str(pred.get("direction") or "")
            confidence = float(pred.get("confidence") or 0)
            ensemble_up = float((pred.get("layer_outputs") or {}).get("ensemble_up") or 0)
            plan = build_entry_plan(
                symbol,
                histories[symbol],
                prediction=pred,
                capital=capital,
                max_position_pct=SC.MAX_POSITION_PCT,
                name=name_map.get(symbol, ""),
            )
            plan["factor_score"] = round(float(cand.get("score") or 0), 4)
            # Lead with the transparent momentum/trend factor; ML up-probability is a
            # secondary confirmation (local backtests showed no edge over majority baseline).
            plan["rank_score"] = round(
                SC.RANK_W_FACTOR * float(cand.get("score") or 0)
                + SC.RANK_W_ENSEMBLE_UP * ensemble_up
                + SC.RANK_W_CONFIDENCE * confidence,
                4,
            )
            if direction == "up":
                up_picks.append(plan)
            else:
                fallback_picks.append(plan)

        up_picks.sort(key=lambda x: x["rank_score"], reverse=True)
        fallback_picks.sort(key=lambda x: x["rank_score"], reverse=True)

        picks = up_picks[: max(1, int(top_n))]
        if len(picks) < int(top_n):
            picks.extend(fallback_picks[: int(top_n) - len(picks)])
        picks.sort(key=lambda x: x["rank_score"], reverse=True)

        payload = {
            "generated_at": datetime.now().isoformat(),
            "top_n": int(top_n),
            "capital": float(capital),
            "min_confidence": float(min_confidence),
            "universe": {
                "total": len(stocks),
                "pool": len(pool),
                "loaded": len(histories),
                "picked": len(picks),
            },
            "picks": picks,
            "skipped": skipped,
            "risk_note": "Research output only; not investment advice.",
        }
        self._save_daily_picks(payload)
        return payload

    def _daily_picks_path(self) -> Path:
        return Path(__file__).parent.parent / "data" / "daily_picks.json"

    def _save_daily_picks(self, payload: Dict[str, Any]) -> None:
        path = self._daily_picks_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_daily_picks(self) -> Optional[Dict[str, Any]]:
        path = self._daily_picks_path()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def run_trading_agents_review(self, symbol: str) -> Dict[str, Any]:
        from flask_services.trading_agents_bridge import trading_agents_bridge
        prediction = self._get_prediction_service().predict_stock(symbol, horizon=5, up_threshold=0.02, record_signal=False)
        history = self._get_prediction_service()._load_history_df(symbol)
        from research.decision_engine import analyze_holding
        context = analyze_holding(symbol, history, 100, 100, float(history.iloc[-1]["close_price"]), prediction)
        return trading_agents_bridge.analyze(symbol, context)

    def list_users_with_auto_advance(self) -> List[int]:
        payload = self._load_investments()
        users = []
        for uid, bucket in (payload.get("by_user") or {}).items():
            cfg = bucket.get("config") or {}
            if cfg.get("auto_advance_paper"):
                users.append(int(uid))
        return users

    @staticmethod
    def _target_weights_from_signals(
        symbols: List[str],
        signals: Dict[str, Dict[str, Any]],
        weight_mode: str,
        min_confidence: float,
        max_total: float,
    ) -> Dict[str, float]:
        eligible = []
        for sym in symbols:
            sig = signals.get(sym) or {}
            if int(sig.get("prediction", 0)) != 1:
                continue
            conf = float(sig.get("confidence") or 0)
            if conf < min_confidence:
                continue
            eligible.append((sym, conf))

        if not eligible:
            return {}

        if weight_mode == "signal":
            total_conf = sum(c for _, c in eligible) or 1.0
            raw = {sym: (c / total_conf) * max_total for sym, c in eligible}
        else:
            w = max_total / len(eligible)
            raw = {sym: w for sym, _ in eligible}

        cap = max_total / max(len(raw), 1)
        return {sym: min(w, cap) for sym, w in raw.items()}


investment_service = InvestmentService()
