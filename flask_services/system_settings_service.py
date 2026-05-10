"""
Persistent system settings for admin-managed runtime config.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict


class SystemSettingsService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = Path(__file__).parent.parent / "data" / "system_settings.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _default_payload(self) -> Dict[str, Any]:
        return {
            "ai": {},
            "data_source": {},
        }

    def load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return self._default_payload()
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return self._default_payload()
            base = self._default_payload()
            for key in ("ai", "data_source"):
                val = payload.get(key)
                if isinstance(val, dict):
                    base[key] = val
            return base
        except Exception:
            return self._default_payload()

    def save(self, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def apply_runtime(self, ai_service: Any, data_service: Any) -> Dict[str, Any]:
        payload = self.load()
        ai_payload = payload.get("ai", {})
        ds_payload = payload.get("data_source", {})

        if isinstance(ai_payload, dict) and ai_payload:
            ai_service.update_runtime_config(ai_payload)

        stock_source = str(ds_payload.get("stock_source") or "").strip()
        if stock_source:
            data_service.set_stock_source(stock_source)

        return payload

    def update_settings(
        self,
        ai_service: Any,
        data_service: Any,
        ai_patch: Dict[str, Any] | None = None,
        data_source_patch: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        payload = self.load()
        if isinstance(ai_patch, dict):
            payload.setdefault("ai", {}).update(ai_patch)
        if isinstance(data_source_patch, dict):
            payload.setdefault("data_source", {}).update(data_source_patch)
        self.save(payload)

        # Apply after persistence.
        self.apply_runtime(ai_service, data_service)
        return self.load()


system_settings_service = SystemSettingsService()
