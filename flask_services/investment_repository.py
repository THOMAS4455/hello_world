"""Storage abstraction for investment data (JSON default, PostgreSQL-ready)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG_KEYS = {
    "risk_level",
    "weight_mode",
    "max_position_pct",
    "max_total_equity_pct",
    "horizon",
    "up_threshold",
    "min_confidence",
    "initial_capital",
    "label_mode",
    "auto_advance_paper",
    "max_symbols",
}


class InvestmentRepository(ABC):
    @abstractmethod
    def load_investments(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def save_investments(self, payload: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def load_paper(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def save_paper(self, payload: Dict[str, Any]) -> None:
        ...


class JsonInvestmentRepository(InvestmentRepository):
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._investments_file = data_dir / "user_investments.json"
        self._paper_file = data_dir / "paper_accounts.json"

    def load_investments(self) -> Dict[str, Any]:
        if not self._investments_file.exists():
            return {"by_user": {}}
        try:
            payload = json.loads(self._investments_file.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {"by_user": {}}
        except Exception:
            return {"by_user": {}}

    def save_investments(self, payload: Dict[str, Any]) -> None:
        self._investments_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_paper(self) -> Dict[str, Any]:
        if not self._paper_file.exists():
            return {"by_user": {}}
        try:
            payload = json.loads(self._paper_file.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {"by_user": {}}
        except Exception:
            return {"by_user": {}}

    def save_paper(self, payload: Dict[str, Any]) -> None:
        self._paper_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
