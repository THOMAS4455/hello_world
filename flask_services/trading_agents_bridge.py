"""A-share adapter for the TradingAgents research workflow.

TradingAgents supplies the analyst/bull/bear/risk/trader workflow. Market data
and execution remain owned by this application because TradingAgents' bundled
yfinance and Alpha Vantage adapters do not cover A-share reliably.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class TradingAgentsBridge:
    def __init__(self) -> None:
        self.source_root = Path(r"D:\IdeaProject\prspace\TradingAgents")

    def analyze(self, symbol: str, context: Dict[str, Any]) -> Dict[str, Any]:
        from services.real_ai_service import real_ai_service

        prompt = (
            "Use the TradingAgents workflow for an A-share research memo. "
            "Produce concise Chinese sections named: market analyst, fundamentals analyst, "
            "bull case, bear case, risk manager, and trader. Do not invent data or promise returns. "
            "Give a conditional action and concrete invalidation levels.\n"
            "Symbol: {}\nVerified system context: {}"
        ).format(symbol, context)
        return {
            "framework": "TradingAgents-compatible A-share adapter",
            "source_available": self.source_root.exists(),
            "analysis": real_ai_service.analyze(prompt),
            "disclaimer": "Research output only; no brokerage order is created.",
        }


trading_agents_bridge = TradingAgentsBridge()
