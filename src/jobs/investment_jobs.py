"""Scheduled jobs for investment platform maintenance."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler = None


def resolve_all_signal_outcomes() -> int:
    from flask_services.investment_service import investment_service

    updated = investment_service._resolve_signals_lazy()
    logger.info("Resolved %s pending signal outcomes", updated)
    return updated


def auto_advance_paper_accounts() -> int:
    from flask_services.investment_service import investment_service

    advanced = 0
    for user_id in investment_service.list_users_with_auto_advance():
        try:
            investment_service.advance_paper_day(user_id)
            advanced += 1
        except Exception as exc:
            logger.warning("Auto advance failed for user %s: %s", user_id, exc)
    logger.info("Auto-advanced %s paper accounts", advanced)
    return advanced


def run_daily_screener_job(top_n: int = 5) -> int:
    from flask_services.investment_service import investment_service

    try:
        result = investment_service.run_daily_screener(top_n=top_n)
        picked = int((result.get("universe") or {}).get("picked", 0))
        logger.info("Daily screener picked %s stocks", picked)
        return picked
    except Exception as exc:
        logger.warning("Daily screener failed: %s", exc)
        return 0


def run_live_validation(skip_fetch: bool = False) -> dict:
    """Refresh bars, settle outcomes and rewrite the live performance report.

    Delegates to scripts/daily_live_validation.py so the in-process scheduler and
    the Windows Task Scheduler fallback share exactly one implementation.
    """
    import json
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))

    import daily_live_validation as dlv  # noqa: E402  (path set up above)

    argv = ["--skip-fetch"] if skip_fetch else []
    exit_code = dlv.run(dlv.parse_args(argv))

    latest_path = root / "data" / "live_eval" / "latest.json"
    summary = {"exit_code": exit_code}
    if latest_path.exists():
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
        summary.update(
            {
                "n_resolved": payload.get("n_resolved"),
                "edge": payload.get("edge"),
                "baseline_accuracy": payload.get("baseline_accuracy"),
                "insufficient_n": payload.get("insufficient_n"),
                "status": payload.get("status"),
            }
        )
    logger.info("Live validation finished: %s", summary)
    return summary


def run_daily_investment_jobs() -> None:
    resolve_all_signal_outcomes()
    auto_advance_paper_accounts()


def start_investment_scheduler() -> Optional[object]:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler not installed; investment jobs disabled")
        return None

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        run_daily_investment_jobs,
        CronTrigger(hour=16, minute=30),
        id="investment_daily_jobs",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_screener_job,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=30),
        id="daily_screener_job",
        replace_existing=True,
    )
    # Runs after the close, once the day's bars are final. 16:45 leaves the
    # 16:30 outcome-resolution job time to finish first.
    scheduler.add_job(
        run_live_validation,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=45),
        id="live_validation_job",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Investment scheduler started (daily 16:30)")
    return scheduler


def stop_investment_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
