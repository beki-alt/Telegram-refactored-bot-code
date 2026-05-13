"""
admin/reminders.py
───────────────────
Automated JobQueue tasks:
  - send_payment_start_reminder  — fires on billing start day
  - send_one_day_reminder        — fires one day before billing end day
  - send_final_day_reminder      — fires on billing end day
  - monthly_cycle_reset_job      — fires the day after end day; resets all users to unpaid
                                   and sends a summary report to all admins
"""

import logging

from telegram.ext import ContextTypes

import config
import database as db
from texts import T
from utils import eth_month_name, format_eth_datetime, now_eth, to_ethiopian

logger = logging.getLogger(__name__)


async def send_payment_start_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast the payment-start message to ALL users."""
    if db.get_setting("notify_payment_start", "true") != "true":
        return

    cycle    = db.get_billing_cycle()
    template = db.get_setting("msg_payment_start", T.DEFAULT_MSG_PAYMENT_START)
    msg      = template.format(start_day=cycle["start"], end_day=cycle["end"])

    users = db.get_all_users()
    for user in users:
        try:
            await context.bot.send_message(chat_id=user["telegram_id"], text=msg)
        except Exception as exc:
            logger.warning(f"Payment-start reminder failed for {user['telegram_id']}: {exc}")

    logger.info(f"Payment-start reminder sent to {len(users)} users.")


async def send_one_day_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a one-day-before-deadline reminder to unpaid users only."""
    if db.get_setting("notify_one_day", "true") != "true":
        return

    cycle    = db.get_billing_cycle()
    template = db.get_setting("msg_reminder_one_day", T.DEFAULT_MSG_ONE_DAY)
    msg      = template.format(end_day=cycle["end"])

    unpaid = db.get_unpaid_users()
    for user in unpaid:
        try:
            await context.bot.send_message(chat_id=user["telegram_id"], text=msg)
        except Exception as exc:
            logger.warning(f"One-day reminder failed for {user['telegram_id']}: {exc}")

    logger.info(f"One-day reminder sent to {len(unpaid)} unpaid users.")


async def send_final_day_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a final-day reminder to unpaid users only."""
    if db.get_setting("notify_final_day", "true") != "true":
        return

    cycle    = db.get_billing_cycle()
    template = db.get_setting("msg_final_day", T.DEFAULT_MSG_FINAL_DAY)
    msg      = template.format(end_day=cycle["end"])

    unpaid = db.get_unpaid_users()
    for user in unpaid:
        try:
            await context.bot.send_message(chat_id=user["telegram_id"], text=msg)
        except Exception as exc:
            logger.warning(f"Final-day reminder failed for {user['telegram_id']}: {exc}")

    logger.info(f"Final-day reminder sent to {len(unpaid)} unpaid users.")


async def monthly_cycle_reset_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Monthly cycle reset:
      1. Capture cycle summary BEFORE resetting (so numbers are accurate).
      2. Reset ALL users to 'unpaid'.
      3. Send a detailed Amharic summary report to every admin.
    """
    now = now_eth()
    eth_year, eth_month, eth_day = to_ethiopian(now)

    # Determine which Ethiopian month just closed
    if eth_day == 1:
        closing_month = eth_month - 1 if eth_month > 1 else 13
        closing_year  = eth_year if eth_month > 1 else eth_year - 1
    else:
        closing_month = eth_month
        closing_year  = eth_year

    logger.info(f"Monthly reset: closing cycle {eth_month_name(closing_month)} {closing_year}.")

    # Step 1 — capture summary
    summary = db.get_cycle_summary(closing_month, closing_year)

    # Step 2 — reset users
    db.reset_all_users_to_unpaid()
    logger.info(f"All {summary['total_users']} users reset to 'unpaid'.")

    # Step 3 — build report
    pct    = (
        round(summary["total_paid"] / summary["total_users"] * 100)
        if summary["total_users"] > 0 else 0
    )
    filled = round(pct / 10)
    bar    = "█" * filled + "░" * (10 - filled)

    unpaid_lines = [
        f"  • {u['name']} (`{u['telegram_id']}`)"
        for u in summary["unpaid_users"][:10]
    ]
    unpaid_list = "\n".join(unpaid_lines) if unpaid_lines else T.CYCLE_UNPAID_ALL_PAID
    if len(summary["unpaid_users"]) > 10:
        unpaid_list += T.CYCLE_UNPAID_MORE.format(n=len(summary["unpaid_users"]) - 10)

    report = T.CYCLE_RESET_REPORT.format(
        month_name     = eth_month_name(closing_month),
        year           = closing_year,
        total          = summary["total_users"],
        paid           = summary["total_paid"],
        unpaid         = summary["total_unpaid"],
        pending        = summary["total_pending"],
        rejected       = summary["total_rejected"],
        pct            = pct,
        bar            = bar,
        unpaid_list    = unpaid_list,
        reset_datetime = format_eth_datetime(now),
    )

    # Step 4 — notify all admins
    admins    = db.get_all_admins()
    admin_ids = {a["telegram_id"] for a in admins}
    if config.ADMIN_ID:
        admin_ids.add(config.ADMIN_ID)

    notified = 0
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                chat_id    = admin_id,
                text       = report,
                parse_mode = "Markdown",
            )
            notified += 1
        except Exception as exc:
            logger.warning(f"Could not send reset report to admin {admin_id}: {exc}")

    logger.info(f"Monthly reset report sent to {notified} admin(s).")
