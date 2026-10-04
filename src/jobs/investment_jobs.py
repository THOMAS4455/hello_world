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
    scheduler.start()
    _scheduler = scheduler
    logger.info("Investment scheduler started (daily 16:30)")
    return scheduler


def stop_investment_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
