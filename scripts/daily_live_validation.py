#!/usr/bin/env python3
"""Daily live-data validation: refresh bars, settle outcomes, report performance.

Single entry point shared by both triggers:

* in-process scheduler (src/jobs/investment_jobs.py, 16:30 local), and
* Windows Task Scheduler fallback (scripts/register_daily_task.ps1).

Contract:

1. Refresh qfq daily bars for every symbol that has an unresolved signal.
2. Resolve matured signal outcomes from those bars (point-in-time entry index).
3. Write the full-population performance report to data/live_eval/.

A fetch failure keeps previously stored bars and marks the day partial; the
script NEVER substitutes synthetic data (that pattern is what made the old
"real data" scripts misleading).

Usage:
    python scripts/daily_live_validation.py [--skip-fetch] [--symbols 600519,000001]
                                            [--min-samples 200] [--lookback-days 400]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _p in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

LOG_DIR = PROJECT_ROOT / "logs" / "live_validation"

# Upstream data hosts drop connections under rapid sequential requests; retry with
# backoff and keep a gap between symbols instead of losing the whole day's fetch.
FETCH_ATTEMPTS = 3
FETCH_BACKOFF_SEC = 2.0


def _log(message: str, handle=None) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    line = "[%s] %s" % (stamp, message)
    print(line, flush=True)
    if handle is not None:
        handle.write(line + "\n")
        handle.flush()


def _pending_symbols() -> List[str]:
    from validation.performance_report import load_resolved_logs

    payload = load_resolved_logs()
    out: Set[str] = set()
    path = Path(payload["path"])
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        for entry in raw.get("logs") or []:
            if not entry.get("outcome_resolved") and entry.get("symbol"):
                out.add(str(entry["symbol"]).strip())
    return sorted(out)


def refresh_bars(symbols: List[str], lookback_days: int, handle) -> Dict[str, Any]:
    """Fetch qfq daily bars into the local store; never fabricate data."""
    from core.akshare_data_collector import AKShareDataCollector
    from validation.market_store import MarketStore

    store = MarketStore()
    collector = AKShareDataCollector()
    start_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  - __import__("datetime").timedelta(days=lookback_days))
    start = start_date.strftime("%Y%m%d")

    fetched, failed, rows = 0, [], 0
    for index, symbol in enumerate(symbols):
        history = None
        last_error = None
        # Upstream data hosts reset connections when hit in a tight loop, so retry
        # each symbol a couple of times with backoff before giving up.
        for attempt in range(1, FETCH_ATTEMPTS + 1):
            try:
                history = collector.get_stock_history(symbol=symbol, start_date=start)
                if history:
                    break
                last_error = "empty history"
            except Exception as exc:
                last_error = str(exc)
            if attempt < FETCH_ATTEMPTS:
                time.sleep(FETCH_BACKOFF_SEC * attempt)

        if not history:
            failed.append({"symbol": symbol, "error": last_error or "unknown"})
            _log("no bars for %s after %d attempt(s): %s" % (symbol, FETCH_ATTEMPTS, last_error), handle)
        else:
            import pandas as pd

            df = pd.DataFrame(history)
            written = store.upsert_bars(symbol, df, adj="qfq", source="akshare")
            rows += written
            fetched += 1
            _log("stored %d rows for %s" % (written, symbol), handle)

        if index < len(symbols) - 1:
            time.sleep(FETCH_BACKOFF_SEC)

    return {
        "symbols_requested": len(symbols),
        "symbols_fetched": fetched,
        "symbols_failed": failed,
        "rows_written": rows,
        "coverage": store.coverage(),
    }


def resolve_outcomes(handle) -> Dict[str, Any]:
    """Settle every matured signal using the local bar store."""
    from validation.market_store import MarketStore, load_bars_as_history
    from validation.outcome_resolver import OutcomeResolver
    from validation.signal_tracker import SignalTracker

    store = MarketStore()
    tracker = SignalTracker()
    resolver = OutcomeResolver(
        signal_tracker=tracker,
        price_loader=lambda symbol: load_bars_as_history(store, symbol),
        label_mode="fixed_horizon",
    )
    updated = resolver.resolve_pending(label_mode="fixed_horizon")
    _log("resolved %d pending signal outcome(s)" % updated, handle)
    return {"resolved_now": updated, "coverage": store.coverage()}


def build_and_write_report(min_samples: int, counters: Dict[str, Any], handle) -> Dict[str, Any]:
    from validation.performance_report import (
        build_report,
        load_resolved_logs,
        summarize_for_log,
        write_report,
    )

    payload = load_resolved_logs()
    report = build_report(payload["resolved"], min_samples=min_samples)
    report["n_pending"] = payload["pending"]
    report["n_total_logs"] = payload["total"]
    report["status"] = counters.get("status", "ok")
    report["data"] = counters
    paths = write_report(report, counters=None)
    _log(summarize_for_log(report), handle)
    _log("report written: %s" % paths["latest"], handle)
    if report.get("reconciliation_mismatch"):
        _log("WARNING: stored outcome_correct flags disagree with recomputed labels", handle)
    return {**report, "paths": paths}


def run(args: argparse.Namespace) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / ("%s.log" % datetime.now().strftime("%Y%m%d"))
    started = time.time()

    with log_path.open("a", encoding="utf-8") as handle:
        _log("daily live validation start (mode=%s)" % ("skip-fetch" if args.skip_fetch else "full"), handle)
        status = "ok"
        fetch_info: Dict[str, Any] = {"skipped": True}
        symbols = sorted(set(_pending_symbols()) | set(args.symbols or []))
        _log("symbols with pending signals: %d" % len(symbols), handle)

        try:
            if not args.skip_fetch and symbols:
                fetch_info = refresh_bars(symbols, args.lookback_days, handle)
                if fetch_info.get("symbols_failed"):
                    status = "partial"
            elif not args.skip_fetch:
                _log("nothing to fetch (no pending signals)", handle)

            resolve_info = resolve_outcomes(handle)
            counters = {"status": status, "fetch": fetch_info, "resolve": resolve_info,
                        "elapsed_sec": round(time.time() - started, 2)}
            report = build_and_write_report(args.min_samples, counters, handle)
            _log("done in %.1fs" % (time.time() - started), handle)
            print(json.dumps({
                "status": status,
                "n_resolved": report.get("n_resolved"),
                "edge": report.get("edge"),
                "baseline_accuracy": report.get("baseline_accuracy"),
                "insufficient_n": report.get("insufficient_n"),
                "latest": report["paths"]["latest"],
            }, ensure_ascii=False, indent=2))
        except Exception:
            status = "failed"
            _log("FATAL:\n" + traceback.format_exc(), handle)
            print(json.dumps({"status": "failed"}, ensure_ascii=False))
            return 1

    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="daily live-data validation")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="do not hit the network; settle and report from stored bars")
    parser.add_argument("--symbols", type=lambda s: [x.strip() for x in s.split(",") if x.strip()],
                        default=None, help="extra symbols to refresh, comma separated")
    parser.add_argument("--min-samples", type=int, default=200,
                        help="below this the report is marked insufficient_n")
    parser.add_argument("--lookback-days", type=int, default=400,
                        help="how many calendar days of bars to refresh")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(run(parse_args()))
