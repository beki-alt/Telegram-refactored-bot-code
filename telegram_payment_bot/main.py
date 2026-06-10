"""
main.py
────────
Application entry point.

FIXES applied:
 - build_start_conversation() registered as a ConversationHandler (not a plain
   CommandHandler) so the phone-collection flow works for new users.
 - Removed duplicate standalone CallbackQueryHandler for profile_edit_name
   (it was registered both here AND inside build_profile_conversation()).
 - All imports updated to match fixed handler signatures.
 - Payment-schedule view wired directly via MessageHandler.
"""

import asyncio
import json
import logging
from datetime import time as dt_time

from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import (
    Application,
    ApplicationBuilder,
    MessageHandler,
    filters,
)

import config
import database.client as db
from admin.conversation import build_admin_conversation
from admin.reminders import (
    monthly_cycle_reset_job,
    send_final_day_reminder,
    send_one_day_reminder,
    send_payment_start_reminder,
)
from handlers import (
    build_payment_conversation,
    build_profile_conversation,
    build_start_conversation,
    build_support_conversation,
    handle_unknown,
    show_profile,
    support_and_history,
)
from handlers.payment import pay_renew
from keep_alive import keep_alive
from texts import T
from utils import ETH_TZ, effective_end_day, eth_days_in_month, now_eth, to_ethiopian

config.setup_logging()
logger = logging.getLogger(__name__)

_STATE_PREFIX = "BOT_STATE:"


async def _save_channel_state(bot, updates: dict) -> None:
    """
    Merge `updates` into the pinned state message in the private channel.

    The pinned message is a single JSON blob prefixed with _STATE_PREFIX.
    On success the old pin is replaced with the new one so the channel stays
    tidy.  All errors are caught and logged — a failed save never crashes a
    reminder job.
    """
    ch = config.PRIVATE_CHANNEL_ID
    if not ch:
        return
    try:
        chat = await bot.get_chat(ch)
        existing: dict = {}
        pm = chat.pinned_message
        if pm and pm.text and pm.text.startswith(_STATE_PREFIX):
            existing = json.loads(pm.text[len(_STATE_PREFIX):])
        existing.update(updates)
        sent = await bot.send_message(chat_id=ch, text=_STATE_PREFIX + json.dumps(existing))
        await bot.pin_chat_message(
            chat_id=ch,
            message_id=sent.message_id,
            disable_notification=True,
        )
        logger.info(f"Channel state saved: {list(updates.keys())}")
    except Exception as exc:
        logger.warning(f"Channel state save failed: {exc}")


async def _load_channel_state(bot) -> dict:
    """
    Read the pinned state blob from the private channel.

    Returns an empty dict if the channel is not configured, the pin is
    missing, or any error occurs.
    """
    ch = config.PRIVATE_CHANNEL_ID
    if not ch:
        return {}
    try:
        chat = await bot.get_chat(ch)
        pm = chat.pinned_message
        if pm and pm.text and pm.text.startswith(_STATE_PREFIX):
            state = json.loads(pm.text[len(_STATE_PREFIX):])
            logger.info(f"Channel state loaded: {list(state.keys())}")
            return state
    except Exception as exc:
        logger.warning(f"Channel state load failed: {exc}")
    return {}


# ── Payment schedule handler (standalone — no conversation state needed) ──────

async def payment_schedule(update, context) -> None:
    """Show the billing schedule for the current Ethiopian month."""
    from utils import eth_month_name
    tg_id = update.effective_user.id
    user  = db.get_user(tg_id)

    cycle = db.get_billing_cycle()
    now   = now_eth()
    eth_year, eth_month, eth_day = to_ethiopian(now)
    days_in_month = eth_days_in_month(eth_year, eth_month)

    start = cycle["start"]
    # Cap end at the real last day of the current Ethiopian month.
    # For months 1–12 this is always 30 so end_day=30 stays 30.
    # For Pagume (month 13, 5–6 days) end_day=30 would be capped to 5 or 6.
    end = effective_end_day(eth_year, eth_month, cycle["end"])

    # ── Days-remaining calculation ─────────────────────────────────────────────
    # With the default same-month window (start=25, end=30) start<=end is always
    # true for months 1-12.  Cross-month (start>end, e.g. 25→5) is also handled
    # for admins who choose that configuration.
    if start <= end:
        # ── Same-month window ─────────────────────────────────────────────────
        if start <= eth_day <= end:
            days_remaining = end - eth_day          # 0 on last day
        elif eth_day < start:
            days_remaining = -(start - eth_day)     # negative → days until open
        else:
            # Past end, closed for this cycle — show days to next start
            days_remaining = -(days_in_month - eth_day + start)
    else:
        # ── Cross-month window (e.g. start=25, end=5) ─────────────────────────
        if eth_day >= start:
            days_remaining = days_in_month - eth_day + end  # days left in window
        elif eth_day <= end:
            days_remaining = end - eth_day                   # days left in window
        else:
            # Between end+1 and start-1 → closed, show days to start
            days_remaining = -(start - eth_day)

    # ── Build status line ──────────────────────────────────────────────────────
    user_status = user["status"] if user else "unpaid"
    status_icon = T.STATUS_PAID if user_status == "paid" else T.STATUS_UNPAID

    # ── Build event text ───────────────────────────────────────────────────────
    if days_remaining is None or days_remaining < 0:
        days_to_start = abs(days_remaining) if days_remaining is not None else 0
        if days_to_start <= 1:
            next_event = T.SCHEDULE_NEXT_START.format(start=start)
        else:
            next_event = T.SCHEDULE_DAYS_TO_START.format(days=days_to_start)
    elif days_remaining == 0:
        next_event = T.SCHEDULE_LAST_DAY
    elif days_remaining == 1:
        next_event = T.SCHEDULE_ONE_DAY_LEFT
    else:
        next_event = T.SCHEDULE_DAYS_LEFT.format(days=days_remaining)

    text = (
        f"{T.SCHEDULE_HEADER}\n\n"
        f"{T.SCHEDULE_MONTH.format(month_name=eth_month_name(eth_month), year=eth_year)}\n"
        f"{T.SCHEDULE_CYCLE.format(start=start, end=end)}\n"
        f"{T.SCHEDULE_USER_STATUS.format(status=status_icon)}\n\n"
        f"{T.SCHEDULE_DIVIDER}\n"
        f"{T.SCHEDULE_NEXT.format(event=next_event)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Application post-init ─────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Called once after the Application is fully initialized."""

    # 1. Database — seed default settings
    try:
        db.init_tables()
        logger.info("Database initialized.")
    except Exception as exc:
        logger.error(f"Database init error: {exc}")

    # 2. Ensure super admin exists in DB
    if config.ADMIN_ID:
        db.add_admin(config.ADMIN_ID, config.ADMIN_ID, is_super=True)
        logger.info(f"Super admin ensured: {config.ADMIN_ID}")

    # 3. Set bot command list visible in Telegram menu.
    #    Default scope (all users): /start and /cancel only — /admin is hidden.
    #    Admin scope (per admin chat): also shows /admin.
    public_commands = [
        BotCommand("start",  T.CMD_START_DESC),
        BotCommand("cancel", T.CMD_CANCEL_DESC),
    ]
    admin_commands = [
        BotCommand("start",  T.CMD_START_DESC),
        BotCommand("cancel", T.CMD_CANCEL_DESC),
        BotCommand("admin",  T.CMD_ADMIN_DESC),
    ]
    await application.bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())

    # Set /admin visible only in each admin's private chat
    admin_ids = {row["telegram_id"] for row in db.get_all_admins()}
    if config.ADMIN_ID:
        admin_ids.add(config.ADMIN_ID)
    for admin_id in admin_ids:
        try:
            await application.bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception as exc:
            logger.warning(f"Could not set admin commands for {admin_id}: {exc}")

    # 4. Start Supabase keep-alive background coroutine
    asyncio.ensure_future(db.ping_supabase())
    logger.info("Supabase keep-alive scheduled.")

    # 5. Schedule daily reminder jobs
    job_queue = application.job_queue
    if job_queue is None:
        logger.warning("JobQueue unavailable — automated reminders will not run.")
        return

    async def _payment_start_guard(ctx):
        """
        Fire the payment-start broadcast if today is the billing start day and
        the notification has not already been sent in this bot session.

        Three run_daily instances call this guard (noon, 5 pm, 10 pm) so that
        if the bot misses one window it retries at the next.  In-memory bot_data
        is used as the idempotency key within a single session (no new DB field).
        The startup catch-up check uses the existing last_payment_start_eth_date
        setting for cross-restart idempotency.
        """
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        if eth_day != cycle["start"]:
            return

        today_str = f"{eth_year}-{eth_month:02d}-{eth_day:02d}"
        if ctx.bot_data.get("payment_start_sent_date") == today_str:
            logger.info("Payment-start guard: already sent today (in-memory) — skipping.")
            return

        await send_payment_start_reminder(ctx)
        ctx.bot_data["payment_start_sent_date"] = today_str
        await _save_channel_state(ctx.application.bot, {"payment_start_sent_date": today_str})

    async def _one_day_guard(ctx):
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        days  = eth_days_in_month(eth_year, eth_month)
        end   = effective_end_day(eth_year, eth_month, cycle["end"])

        # Cross-month window (start > configured end, e.g. 25 → 5):
        # The guard day (end-1) appears TWICE per calendar month — once before
        # the window opens and once inside the window.  Only fire when the
        # payment-start reminder has already been sent for this cycle
        # (i.e. last_payment_start_eth_date is more recent than last_reset_eth_date).
        if cycle["start"] > cycle["end"]:
            last_ps    = db.get_setting("last_payment_start_eth_date", "")
            last_reset = db.get_setting("last_reset_eth_date", "")
            if not last_ps or last_ps <= last_reset:
                return  # Window not yet open this cycle — skip

        one_before = end - 1 if end > 1 else days
        if eth_day != one_before:
            return

        today_str = f"{eth_year}-{eth_month:02d}-{eth_day:02d}"
        if ctx.bot_data.get("one_day_reminder_sent_date") == today_str:
            logger.info("One-day guard: already sent today (in-memory) — skipping.")
            return

        await send_one_day_reminder(ctx)
        ctx.bot_data["one_day_reminder_sent_date"] = today_str
        await _save_channel_state(ctx.application.bot, {"one_day_reminder_sent_date": today_str})

    async def _final_day_guard(ctx):
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        end   = effective_end_day(eth_year, eth_month, cycle["end"])

        # Same cross-month guard as _one_day_guard above.
        if cycle["start"] > cycle["end"]:
            last_ps    = db.get_setting("last_payment_start_eth_date", "")
            last_reset = db.get_setting("last_reset_eth_date", "")
            if not last_ps or last_ps <= last_reset:
                return

        if eth_day != end:
            return

        today_str = f"{eth_year}-{eth_month:02d}-{eth_day:02d}"
        if ctx.bot_data.get("final_day_reminder_sent_date") == today_str:
            logger.info("Final-day guard: already sent today (in-memory) — skipping.")
            return

        await send_final_day_reminder(ctx)
        ctx.bot_data["final_day_reminder_sent_date"] = today_str
        await _save_channel_state(ctx.application.bot, {"final_day_reminder_sent_date": today_str})

    async def _monthly_reset_guard(ctx):
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        days = eth_days_in_month(eth_year, eth_month)
        end  = effective_end_day(eth_year, eth_month, cycle["end"])
        reset_day = end + 1 if end < days else 1
        if eth_day == reset_day:
            await monthly_cycle_reset_job(ctx)

    # Ethiopian traditional time → standard clock (Africa/Addis_Ababa, UTC+3):
    #   12:00 Ethiopian morning  =  6:00 AM standard
    #    5:00 Ethiopian daytime  = 11:00 AM standard
    #   10:00 Ethiopian afternoon= 4:00 PM standard
    eth_6am   = dt_time( 6, 0,  tzinfo=ETH_TZ)   # 12:00 Ethiopian morning
    eth_11am  = dt_time(11, 0,  tzinfo=ETH_TZ)   #  5:00 Ethiopian daytime
    eth_4pm   = dt_time(16, 0,  tzinfo=ETH_TZ)   # 10:00 Ethiopian afternoon
    midnight_five = dt_time( 0, 5,  tzinfo=ETH_TZ)

    # All three notification guards run at all three daily windows so that a
    # missed window is caught by the next.  In-memory bot_data prevents
    # double-sending within the same bot session.
    job_queue.run_daily(_payment_start_guard, time=eth_6am,  name="payment_start_6am")
    job_queue.run_daily(_payment_start_guard, time=eth_11am, name="payment_start_11am")
    job_queue.run_daily(_payment_start_guard, time=eth_4pm,  name="payment_start_4pm")
    job_queue.run_daily(_one_day_guard,        time=eth_6am,  name="one_day_reminder_6am")
    job_queue.run_daily(_one_day_guard,        time=eth_11am, name="one_day_reminder_11am")
    job_queue.run_daily(_one_day_guard,        time=eth_4pm,  name="one_day_reminder_4pm")
    job_queue.run_daily(_final_day_guard,      time=eth_6am,  name="final_day_reminder_6am")
    job_queue.run_daily(_final_day_guard,      time=eth_11am, name="final_day_reminder_11am")
    job_queue.run_daily(_final_day_guard,      time=eth_4pm,  name="final_day_reminder_4pm")
    job_queue.run_daily(_monthly_reset_guard,  time=midnight_five, name="monthly_cycle_reset")

    logger.info("Automated reminder and monthly reset jobs scheduled.")

    # BUG-11 FIX: Catch up on a missed monthly reset if the bot was offline
    # when the scheduled job should have fired.
    async def _startup_missed_reset_check(ctx):
        """
        One-time job: run the monthly reset immediately if it was missed while
        the bot was down.

        Algorithm:
          1. Compute today's reset_day from the current billing cycle.
          2. If today IS reset_day and 'last_reset_eth_date' in settings does
             NOT equal today's Ethiopian date → the reset was missed → run now.
          3. Otherwise do nothing (job already ran today or today is not reset day).

        'last_reset_eth_date' is written by monthly_cycle_reset_job() every time
        it successfully completes, giving an idempotent single-fire guarantee.
        """
        try:
            now_val = now_eth()
            eth_year, eth_month, eth_day = to_ethiopian(now_val)
            cycle     = db.get_billing_cycle()
            days      = eth_days_in_month(eth_year, eth_month)
            end       = effective_end_day(eth_year, eth_month, cycle["end"])
            reset_day = end + 1 if end < days else 1

            if eth_day != reset_day:
                return   # Not reset day — nothing to catch up on

            today_str  = f"{eth_year}-{eth_month:02d}-{eth_day:02d}"
            last_reset = db.get_setting("last_reset_eth_date", "")

            if last_reset == today_str:
                logger.info("Startup missed-reset check: already ran today — skipping.")
                return

            logger.warning(
                f"Startup missed-reset check: reset was due on {today_str} "
                f"but last recorded reset was '{last_reset}'. Running now."
            )
            await monthly_cycle_reset_job(ctx)
        except Exception as exc:
            logger.error(f"Startup missed-reset check failed: {exc}")

    # Restore bot_data from the private channel pinned message BEFORE the other
    # startup checks run.  Fires at 5 s so it completes before the reset check
    # (10 s) and the payment-start check (15 s).
    async def _startup_load_channel_state(ctx):
        try:
            state = await _load_channel_state(ctx.application.bot)
            if state:
                ctx.application.bot_data.update(state)
                logger.info(f"Startup: restored {len(state)} key(s) from channel state.")
        except Exception as exc:
            logger.error(f"Startup channel state load failed: {exc}")

    job_queue.run_once(_startup_load_channel_state, when=5, name="startup_load_channel_state")
    logger.info("Startup channel-state load scheduled (fires in 5 s).")

    # Delay 10 s so the DB connection pool is fully ready before the check runs.
    job_queue.run_once(_startup_missed_reset_check, when=10, name="startup_missed_reset")
    logger.info("Startup missed-reset check scheduled (fires in 10 s).")

    # Catch up on a missed payment-start notification (same pattern as reset check above).
    # If the bot restarted after noon on the billing start day, run_daily already missed
    # that day's 12:00 slot.  This one-shot job detects and corrects that.
    async def _startup_missed_payment_start_check(ctx):
        """
        One-time job: broadcast the payment-start reminder if the bot restarted
        after noon on the billing start day and the scheduled job was missed.

        Algorithm:
          1. If today is NOT the billing start day → nothing to do.
          2. If 'last_payment_start_eth_date' == today → already sent → skip.
          3. Otherwise → missed → send now.
        """
        try:
            now_val = now_eth()
            eth_year, eth_month, eth_day = to_ethiopian(now_val)
            cycle = db.get_billing_cycle()

            if eth_day != cycle["start"]:
                return  # Not start day — nothing to catch up on

            today_str  = f"{eth_year}-{eth_month:02d}-{eth_day:02d}"
            last_sent  = db.get_setting("last_payment_start_eth_date", "")

            if last_sent == today_str:
                logger.info("Startup missed-payment-start check: already sent today — skipping.")
                return

            logger.warning(
                f"Startup missed-payment-start check: start reminder was due on {today_str} "
                f"but last recorded send was '{last_sent}'. Sending now."
            )
            await send_payment_start_reminder(ctx)
            ctx.bot_data["payment_start_sent_date"] = today_str
            await _save_channel_state(ctx.application.bot, {"payment_start_sent_date": today_str})
        except Exception as exc:
            logger.error(f"Startup missed-payment-start check failed: {exc}")

    job_queue.run_once(_startup_missed_payment_start_check, when=15, name="startup_missed_payment_start")
    logger.info("Startup missed-payment-start check scheduled (fires in 15 s).")


# ── Handler registration ──────────────────────────────────────────────────────

def build_application() -> Application:
    if not config.TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is not set.")

    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ── 1. Admin conversation (highest priority — registered first) ────────────
    app.add_handler(build_admin_conversation())

    # ── 2. Start conversation (phone collection for new users) ─────────────────
    #   Must be registered BEFORE profile/payment conversations so /start is
    #   caught here regardless of whether a user conversation is active.
    app.add_handler(build_start_conversation())

    # ── 3. User conversations ──────────────────────────────────────────────────
    app.add_handler(build_profile_conversation())
    app.add_handler(build_payment_conversation())
    app.add_handler(build_support_conversation())

    # ── 4. Main menu reply-keyboard buttons ────────────────────────────────────
    app.add_handler(MessageHandler(
        filters.Regex(rf"^{T.BTN_MY_PROFILE}$"), show_profile
    ))
    # NOTE: BTN_PAY_RENEW is handled by build_payment_conversation() entry points above.
    # A standalone handler here would be dead code (the ConversationHandler catches it
    # first with allow_reentry=True), so it is intentionally omitted.
    app.add_handler(MessageHandler(
        filters.Regex(rf"^{T.BTN_SCHEDULE}$"), payment_schedule
    ))
    app.add_handler(MessageHandler(
        filters.Regex(rf"^{T.BTN_SUPPORT}$"), support_and_history
    ))

    # ── 5. Unknown text catch-all ──────────────────────────────────────────────
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_unknown
    ))

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("Starting Telegram Payment Bot...")
    keep_alive()
    app = build_application()
    logger.info("Bot is running — polling for updates.")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
