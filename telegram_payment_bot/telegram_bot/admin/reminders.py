"""
admin/reminders.py
───────────────────
Automated JobQueue tasks:
  - send_payment_start_reminder  — fires on billing start day
  - send_one_day_reminder        — fires one day before billing end day
  - send_final_day_reminder      — fires on billing end day
  - monthly_cycle_reset_job      — fires the day after end day; resets all
                                   users to unpaid and sends a summary to admins

FIXES:
 BUG-2:  Reminder messages now use effective_end_day() so Pagume users see
         the correct end day (5 or 6) instead of the configured value (30).
 BUG-10: Closing-month logic now detects cross-month billing windows
         (start > end) and always resolves the closing month as the previous
         calendar month in that case — not the current month.
 BUG-12: All user broadcast loops now use _send_with_retry() which handles
         telegram.error.RetryAfter (rate-limit back-off) and adds a 50 ms
         inter-message delay to stay well under Telegram's 30 msg/s limit.
 BUG-11: monthly_cycle_reset_job() records 'last_reset_eth_date' in DB so
         main.py's startup missed-reset check can skip a double-fire.
"""

import asyncio
import logging

import telegram
from telegram.ext import ContextTypes

import config
import database.client as db
from texts import T
from utils import effective_end_day, eth_days_in_month, eth_month_name, format_eth_datetime, now_eth, to_ethiopian

logger = logging.getLogger(__name__)


# ── Rate-limit-aware send helper ──────────────────────────────────────────────

async def _send_with_retry(bot, chat_id: int, text: str, max_retries: int = 2) -> bool:
    """
    Send a text message, retrying up to max_retries times on Telegram
    rate-limit errors (RetryAfter).  Returns True on success, False otherwise.

    BUG-12 FIX: Without this, a single burst of reminders can exhaust
    Telegram's 30 msg/s limit and cause all subsequent sends in the same
    job to fail silently.
    """
    for attempt in range(max_retries + 1):
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            return True
        except telegram.error.RetryAfter as e:
            wait_sec = e.retry_after + 1
            logger.warning(
                f"Telegram rate limit hit — sleeping {wait_sec}s "
                f"(attempt {attempt + 1}/{max_retries + 1})."
            )
            if attempt < max_retries:
                await asyncio.sleep(wait_sec)
        except Exception as exc:
            logger.warning(f"send_message to {chat_id} failed: {exc}")
            return False
    return False


# ── Reminder senders ──────────────────────────────────────────────────────────

async def send_payment_start_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast the payment-start message to ALL users.

    BUG-2 FIX: Use effective_end_day() for the end_day shown in the message
    so Pagume users see '5' (or '6') instead of the configured '30'.

    Month names are passed so the default template (and any custom template
    that uses {month_name}/{end_month_name}) shows the full Ethiopian date,
    e.g. "ከጥቅምት 24 እስከ ህዳር 5" for a cross-month window.
    Extra kwargs are silently ignored by str.format() for custom templates
    that only use {start_day}/{end_day}.
    """
    if db.get_setting("notify_payment_start", "true") != "true":
        return

    cycle    = db.get_billing_cycle()
    template = db.get_setting("msg_payment_start", T.DEFAULT_MSG_PAYMENT_START)

    eth_year, eth_month, _ = to_ethiopian(now_eth())
    eff_end = effective_end_day(eth_year, eth_month, cycle["end"])

    # For cross-month windows (start > end), the end day falls in the next month.
    is_cross_month = cycle["start"] > cycle["end"]
    if is_cross_month:
        end_eth_month = 1 if eth_month == 13 else eth_month + 1
    else:
        end_eth_month = eth_month

    msg = template.format(
        start_day      = cycle["start"],
        end_day        = eff_end,
        month_name     = eth_month_name(eth_month),
        end_month_name = eth_month_name(end_eth_month),
    )

    users   = db.get_all_users()
    sent    = 0
    for user in users:
        ok = await _send_with_retry(context.bot, user["telegram_id"], msg)
        if ok:
            sent += 1
        await asyncio.sleep(0.05)   # ≈20 msg/s — well under Telegram's 30 msg/s limit

    logger.info(f"Payment-start reminder sent to {sent}/{len(users)} users.")


async def send_one_day_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a one-day-before-deadline reminder to unpaid users only.

    BUG-2 FIX: end_day in message uses effective_end_day() for Pagume correctness.
    Passes end_month_name so the template shows the full Ethiopian date.
    """
    if db.get_setting("notify_one_day", "true") != "true":
        return

    cycle    = db.get_billing_cycle()
    template = db.get_setting("msg_reminder_one_day", T.DEFAULT_MSG_ONE_DAY)

    eth_year, eth_month, _ = to_ethiopian(now_eth())
    eff_end = effective_end_day(eth_year, eth_month, cycle["end"])
    msg     = template.format(end_day=eff_end, end_month_name=eth_month_name(eth_month))

    unpaid = db.get_unpaid_users()
    sent   = 0
    for user in unpaid:
        ok = await _send_with_retry(context.bot, user["telegram_id"], msg)
        if ok:
            sent += 1
        await asyncio.sleep(0.05)

    logger.info(f"One-day reminder sent to {sent}/{len(unpaid)} unpaid users.")


async def send_final_day_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a final-day reminder to unpaid users only.

    BUG-2 FIX: end_day in message uses effective_end_day() for Pagume correctness.
    Passes end_month_name so the template shows the full Ethiopian date.
    """
    if db.get_setting("notify_final_day", "true") != "true":
        return

    cycle    = db.get_billing_cycle()
    template = db.get_setting("msg_final_day", T.DEFAULT_MSG_FINAL_DAY)

    eth_year, eth_month, _ = to_ethiopian(now_eth())
    eff_end = effective_end_day(eth_year, eth_month, cycle["end"])
    msg     = template.format(end_day=eff_end, end_month_name=eth_month_name(eth_month))

    unpaid = db.get_unpaid_users()
    sent   = 0
    for user in unpaid:
        ok = await _send_with_retry(context.bot, user["telegram_id"], msg)
        if ok:
            sent += 1
        await asyncio.sleep(0.05)

    logger.info(f"Final-day reminder sent to {sent}/{len(unpaid)} unpaid users.")


async def monthly_cycle_reset_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Monthly cycle reset:
      1. Determine which Ethiopian month JUST CLOSED.
      2. Capture cycle summary BEFORE resetting (so numbers are accurate).
      3. Reset ALL users to 'unpaid'.
      4. Send a detailed Amharic summary report to every admin.
      5. Record 'last_reset_eth_date' in settings for startup idempotency.

    BUG-10 FIX: Closing-month logic now handles cross-month billing windows
    (start > end).  In that configuration the reset fires on day (end+1) of
    the "end month" (e.g. day 6 when end=5), but the cycle STARTED in the
    previous calendar month — so closing_month must be the previous month.

    Logic matrix:
      Same-month window  (start <= end), reset day == 1  → closing = prev month
      Same-month window  (start <= end), reset day > 1   → closing = current month
      Cross-month window (start  > end), reset day == end+1 → closing = prev month
    """
    now = now_eth()
    eth_year, eth_month, eth_day = to_ethiopian(now)
    cycle   = db.get_billing_cycle()
    end_day = effective_end_day(eth_year, eth_month, cycle["end"])

    # ── Determine closing month ────────────────────────────────────────────────
    # For a cross-month window (start > end), the cycle STARTED in the previous
    # month regardless of what day the reset fires.
    # For a same-month window (start <= end):
    #   - reset fires on day (end+1) in the same month → closing = current month
    #   - reset fires on day 1 of the next month (end == last day) → closing = prev month
    cycle_start_day = cycle["start"]
    is_cross_month  = cycle_start_day > cycle["end"]   # Note: raw end, not capped

    if is_cross_month:
        # Billing started in the previous calendar month.
        if eth_month > 1:
            closing_month = eth_month - 1
            closing_year  = eth_year
        else:
            closing_month = 13
            closing_year  = eth_year - 1
    elif eth_day > end_day:
        # Same-month window, reset fired mid-month (e.g. end=15, reset on day 16).
        closing_month = eth_month
        closing_year  = eth_year
    else:
        # Same-month window, reset crossed into new month (end was last day of month).
        if eth_month > 1:
            closing_month = eth_month - 1
            closing_year  = eth_year
        else:
            closing_month = 13
            closing_year  = eth_year - 1

    logger.info(
        f"Monthly reset: closing cycle {eth_month_name(closing_month)} {closing_year} "
        f"(current ET date: day={eth_day}, month={eth_month}, year={eth_year}, "
        f"cross_month={is_cross_month})."
    )

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
        ok = await _send_with_retry(context.bot, admin_id, report)
        if ok:
            notified += 1

    logger.info(f"Monthly reset report sent to {notified} admin(s).")

    # Step 5 — record today's date so the startup missed-reset check (BUG-11)
    # can detect that this job already ran today and skip a duplicate run.
    today_eth_str = f"{eth_year}-{eth_month:02d}-{eth_day:02d}"
    db.set_setting("last_reset_eth_date", today_eth_str)
    logger.info(f"Recorded last_reset_eth_date = {today_eth_str}.")
