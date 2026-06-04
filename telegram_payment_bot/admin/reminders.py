"""
admin/reminders.py
───────────────────
APScheduler-driven reminder jobs + monthly cycle reset.

Phase 7 — Missed-Job Recovery:
  Each job writes its last-run Ethiopian date to the `settings` table under
  keys: last_run_payment_start, last_run_one_day, last_run_final_day,
        last_run_monthly_reset

  On startup, check_missed_jobs() reads these keys and fires any job that
  should have run since the last stored date but didn't.

  Jobs that are recovered are marked with the current date so they are not
  re-fired on subsequent restarts.

Scheduling:
  • send_payment_start_reminder  — fires on billing start day (Ethiopian time)
  • send_one_day_reminder        — fires the day before billing end day
  • send_final_day_reminder      — fires on billing end day
  • monthly_cycle_reset_job      — fires on billing end day + 1 (resets all users)
"""

import asyncio
import logging
from typing import Optional

import database as db
from texts import T
from utils import (
    eth_days_in_month,
    format_eth_date_storage,
    now_eth,
    to_ethiopian,
)

logger = logging.getLogger(__name__)

# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_unpaid_users():
    return db.get_unpaid_users()


def _get_all_admins():
    return db.get_all_admins()


def _is_notification_enabled(key: str) -> bool:
    return db.get_setting(key, "true") == "true"


def _get_message(db_key: str, default: str) -> str:
    return db.get_setting(db_key, default)


def _mark_job_ran(job_key: str) -> None:
    """Record the current Ethiopian date as the last run date for this job."""
    eth_date_str = format_eth_date_storage(now_eth())
    db.set_setting(f"last_run_{job_key}", eth_date_str)


def _get_last_run(job_key: str) -> Optional[str]:
    """Return the stored last-run date string for a job, or ''."""
    return db.get_setting(f"last_run_{job_key}", "")


# ── Reminder jobs ─────────────────────────────────────────────────────────────

async def send_payment_start_reminder(bot, *, mark_run: bool = True) -> int:
    """
    Send the payment-cycle-start notification to all unpaid users.
    Returns the number of messages sent successfully.
    """
    if not _is_notification_enabled("notify_payment_start"):
        logger.info("Payment-start reminder: notifications disabled, skipping.")
        return 0

    cycle   = db.get_billing_cycle()
    message = _get_message("msg_payment_start", T.DEFAULT_MSG_PAYMENT_START).format(
        start_day = cycle["start"],
        end_day   = cycle["end"],
    )

    users = _get_unpaid_users()
    sent  = 0
    for user in users:
        try:
            await bot.send_message(
                chat_id    = user["telegram_id"],
                text       = message,
                parse_mode = "Markdown",
            )
            sent += 1
        except Exception as exc:
            logger.warning(
                f"Payment-start reminder: could not send to {user['telegram_id']}: {exc}"
            )

    if mark_run:
        _mark_job_ran("payment_start")
    logger.info(f"Payment-start reminder sent to {sent}/{len(users)} users.")
    return sent


async def send_one_day_reminder(bot, *, mark_run: bool = True) -> int:
    """
    Send the one-day-left reminder to all unpaid users.
    Returns sent count.
    """
    if not _is_notification_enabled("notify_one_day"):
        return 0

    cycle   = db.get_billing_cycle()
    message = _get_message("msg_reminder_one_day", T.DEFAULT_MSG_ONE_DAY).format(
        end_day = cycle["end"],
    )

    users = _get_unpaid_users()
    sent  = 0
    for user in users:
        try:
            await bot.send_message(
                chat_id    = user["telegram_id"],
                text       = message,
                parse_mode = "Markdown",
            )
            sent += 1
        except Exception as exc:
            logger.warning(
                f"One-day reminder: could not send to {user['telegram_id']}: {exc}"
            )

    if mark_run:
        _mark_job_ran("one_day")
    logger.info(f"One-day reminder sent to {sent}/{len(users)} users.")
    return sent


async def send_final_day_reminder(bot, *, mark_run: bool = True) -> int:
    """
    Send the final-day reminder to all unpaid users.
    Returns sent count.
    """
    if not _is_notification_enabled("notify_final_day"):
        return 0

    cycle   = db.get_billing_cycle()
    message = _get_message("msg_final_day", T.DEFAULT_MSG_FINAL_DAY).format(
        end_day = cycle["end"],
    )

    users = _get_unpaid_users()
    sent  = 0
    for user in users:
        try:
            await bot.send_message(
                chat_id    = user["telegram_id"],
                text       = message,
                parse_mode = "Markdown",
            )
            sent += 1
        except Exception as exc:
            logger.warning(
                f"Final-day reminder: could not send to {user['telegram_id']}: {exc}"
            )

    if mark_run:
        _mark_job_ran("final_day")
    logger.info(f"Final-day reminder sent to {sent}/{len(users)} users.")
    return sent


async def monthly_cycle_reset_job(bot, *, mark_run: bool = True) -> None:
    """
    End-of-cycle job:
      1. Build and send the cycle summary report to all admins.
      2. Reset all users to 'unpaid' for the new cycle.
    """
    now_dt            = now_eth()
    eth_year, eth_month, _ = to_ethiopian(now_dt)
    summary           = db.get_cycle_summary(eth_month, eth_year)

    total    = summary["total_users"]
    paid     = summary["total_paid"]
    unpaid   = summary["total_unpaid"]
    pending  = summary["total_pending"]
    rejected = summary["total_rejected"]
    pct      = round(paid / total * 100) if total else 0
    filled   = int(pct / 5)
    bar      = "█" * filled + "░" * (20 - filled)

    # Build unpaid-users sub-list
    unpaid_users = summary.get("unpaid_users", [])
    if not unpaid_users:
        unpaid_list = T.CYCLE_UNPAID_ALL_PAID
    else:
        lines = [f"  • {u['name']} (`{u['telegram_id']}`)" for u in unpaid_users[:10]]
        if len(unpaid_users) > 10:
            lines.append(T.CYCLE_UNPAID_MORE.format(n=len(unpaid_users) - 10))
        unpaid_list = "\n".join(lines)

    from utils import format_eth_datetime
    report_text = T.CYCLE_RESET_REPORT.format(
        month_name     = summary["month_name"],
        year           = eth_year,
        total          = total,
        paid           = paid,
        unpaid         = unpaid,
        pending        = pending,
        rejected       = rejected,
        pct            = pct,
        bar            = bar,
        unpaid_list    = unpaid_list,
        reset_datetime = format_eth_datetime(now_dt),
    )

    admins = _get_all_admins()
    for admin in admins:
        try:
            await bot.send_message(
                chat_id    = admin["telegram_id"],
                text       = report_text,
                parse_mode = "Markdown",
            )
        except Exception as exc:
            logger.warning(
                f"Cycle reset report: could not send to admin {admin['telegram_id']}: {exc}"
            )

    db.reset_all_users_to_unpaid()
    if mark_run:
        _mark_job_ran("monthly_reset")
    logger.info("Monthly cycle reset completed. All users reset to 'unpaid'.")


# ── Phase 7: Missed-job recovery ─────────────────────────────────────────────

async def check_missed_jobs(bot) -> None:
    """
    Phase 7: Called once on startup. Checks whether any scheduled job missed
    its run while the bot was offline and fires it immediately if so.

    Strategy:
      - Get today's Ethiopian day.
      - Get the stored last-run date for each job.
      - If last-run is empty (never run) or from a previous month, and today
        matches the trigger day (or is past it within the same month/cycle),
        fire the job with mark_run=False so it won't double-fire if the
        scheduler also runs it today.

    Edge cases handled:
      - Cross-month cycles (start=25, end=5).
      - Pagume (13th short month) with only 5-6 days.
      - Bot offline for multiple days — fires each missed job once.
    """
    now_dt                        = now_eth()
    eth_year, eth_month, eth_day  = to_ethiopian(now_dt)
    today_str                     = format_eth_date_storage(now_dt)
    cycle                         = db.get_billing_cycle()
    start_day                     = cycle["start"]
    end_day                       = cycle["end"]

    logger.info(
        f"Missed-job recovery check: today={today_str}, "
        f"cycle={start_day}→{end_day}"
    )

    # helper: has this job already run today?
    def already_ran_today(job_key: str) -> bool:
        return _get_last_run(job_key) == today_str

    # ── Payment start reminder ───────────────────────────────────────────────
    if not already_ran_today("payment_start") and eth_day == start_day:
        logger.warning("Missed-job recovery: firing payment_start reminder now.")
        await send_payment_start_reminder(bot, mark_run=True)
        await _notify_admins_of_recovery(bot, "payment_start")

    # ── One-day reminder (fires the day before end_day) ──────────────────────
    one_day_trigger = _prev_eth_day(eth_year, eth_month, end_day)
    if not already_ran_today("one_day") and eth_day == one_day_trigger:
        logger.warning("Missed-job recovery: firing one_day reminder now.")
        await send_one_day_reminder(bot, mark_run=True)
        await _notify_admins_of_recovery(bot, "one_day")

    # ── Final-day reminder ───────────────────────────────────────────────────
    if not already_ran_today("final_day") and eth_day == end_day:
        logger.warning("Missed-job recovery: firing final_day reminder now.")
        await send_final_day_reminder(bot, mark_run=True)
        await _notify_admins_of_recovery(bot, "final_day")

    # ── Monthly reset (fires day after end_day) ──────────────────────────────
    reset_day = _next_eth_day(eth_year, eth_month, end_day)
    if not already_ran_today("monthly_reset") and eth_day == reset_day:
        logger.warning("Missed-job recovery: firing monthly_cycle_reset now.")
        await monthly_cycle_reset_job(bot, mark_run=True)
        await _notify_admins_of_recovery(bot, "monthly_reset")

    logger.info("Missed-job recovery check complete.")


async def _notify_admins_of_recovery(bot, job_name: str) -> None:
    """Notify admins that a missed job was recovered and fired."""
    admins = _get_all_admins()
    for admin in admins:
        try:
            await bot.send_message(
                chat_id    = admin["telegram_id"],
                text       = T.MISSED_JOB_NOTICE.format(job_name=job_name),
                parse_mode = "Markdown",
            )
        except Exception:
            pass


def _prev_eth_day(eth_year: int, eth_month: int, day: int) -> int:
    """Return the Ethiopian day that is one day before `day` in the same month context."""
    if day > 1:
        return day - 1
    # day == 1: previous day is the last day of previous month
    if eth_month > 1:
        from utils import eth_days_in_month
        return eth_days_in_month(eth_year, eth_month - 1)
    # month == 1, day == 1: previous day is Pagume last day of previous year
    from utils import eth_days_in_month
    return eth_days_in_month(eth_year - 1, 13)


def _next_eth_day(eth_year: int, eth_month: int, day: int) -> int:
    """Return the Ethiopian day that is one day after `day` in the same month context."""
    from utils import eth_days_in_month
    days_in_m = eth_days_in_month(eth_year, eth_month)
    if day < days_in_m:
        return day + 1
    return 1  # wraps to day 1 of next month (month change handled by scheduler)
