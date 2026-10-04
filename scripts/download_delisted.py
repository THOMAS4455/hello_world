#!/usr/bin/env python3
"""Download the A-share delisted-stock list to reduce survivorship bias.

Best-effort: tries the AKShare delist interfaces for SH and SZ exchanges, then
writes a unified list to ``data/delisted_stocks.json``. If the upstream
interfaces are unavailable or change, it degrades gracefully with a clear
message and does not raise.

Usage:
    python scripts/download_delisted.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT = PROJECT_ROOT / "data" / "delisted_stocks.json"


def _fetch() -> list[dict]:
    import akshare as ak

    rows: list[dict] = []
    errors: list[str] = []

    # Shanghai exchange terminated listings
    try:
        sh = ak.stock_info_sh_delist()
        for _, r in sh.iterrows():
            rows.append(
                {
                    "symbol": str(r.get("公司代码", r.get("SECURITY_CODE", ""))).strip(),
                    "name": str(r.get("公司简称", r.get("SECURITY_ABBR", ""))).strip(),
                    "exchange": "SH",
                    "delist_date": str(r.get("终止上市日期", r.get("END_DATE", ""))).strip(),
                }
            )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"SH delist: {exc}")

    # Shenzhen exchange terminated listings
    try:
        sz = ak.stock_info_sz_delist()
        for _, r in sz.iterrows():
            rows.append(
                {
                    "symbol": str(r.get("证券代码", r.get("SECURITY_CODE", ""))).strip(),
                    "name": str(r.get("证券简称", r.get("SECURITY_ABBR", ""))).strip(),
                    "exchange": "SZ",
                    "delist_date": str(r.get("终止上市日期", r.get("END_DATE", ""))).strip(),
                }
            )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"SZ delist: {exc}")

    # dedupe
    seen, uniq = set(), []
    for row in rows:
        key = (row["symbol"], row["exchange"])
        if row["symbol"] and key not in seen:
            seen.add(key)
            uniq.append(row)

    return uniq, errors


def main() -> None:
    rows, errors = _fetch()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"count": len(rows), "stocks": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Delisted stocks saved to {OUT}: {len(rows)} records")
    if errors:
        print("Warnings:")
        for e in errors:
            print("  -", e)
    if not rows:
        print("No delisted records fetched. Survivorship bias remains unresolved; see docs/SURVIVORSHIP_BIAS.md.")
        sys.exit(1)


if __name__ == "__main__":
    main()
