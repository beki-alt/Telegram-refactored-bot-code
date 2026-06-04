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
import logging
from datetime import time as dt_time

from telegram import BotCommand
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


# ── Payment schedule handler (standalone — no conversation state needed) ──────

async def payment_schedule(update, context) -> None:
    """Show the billing schedule for the current month."""
    from utils import eth_month_name
    tg_id = update.effective_user.id
    user  = db.get_user(tg_id)

    cycle                    = db.get_billing_cycle()
    now                      = now_eth()
    eth_year, eth_month, eth_day = to_ethiopian(now)
    days_in_month            = eth_days_in_month(eth_year, eth_month)

    start = cycle["start"]
    # Cap end at the real last day of the current Ethiopian month.
    # For months 1-12 this is always 30 so end_day=30 (e.g. Ginbot 30) stays 30.
    # For Pagume (month 13, 5-6 days) end_day=30 would be capped to 5 or 6.
    end = effective_end_day(eth_year, eth_month, cycle["end"])

    # Days remaining logic
    if start <= end:
        # Same-month billing window
        if start <= eth_day <= end:
            days_remaining = end - eth_day
        elif eth_day < start:
            days_remaining = -(start - eth_day)   # negative = days until start
        else:
            days_remaining = None   # billing closed for this month
    else:
        # Cross-month window (e.g. start=25, end=5)
        if eth_day >= start or eth_day <= end:
            if eth_day >= start:
                days_remaining = days_in_month - eth_day + end
            else:
                days_remaining = end - eth_day
        else:
            days_remaining = -(start - eth_day)

    # Build status line
    user_status = user["status"] if user else "unpaid"
    status_icon = T.STATUS_PAID if user_status == "paid" else T.STATUS_UNPAID

    # Build event text
    if days_remaining is None:
        next_event = T.SCHEDULE_NEXT_START.format(start=start)
    elif days_remaining < 0:
        next_event = T.SCHEDULE_DAYS_TO_START.format(days=abs(days_remaining))
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

    # 3. Set bot command list visible in Telegram menu
    await application.bot.set_my_commands([
        BotCommand("start",  T.CMD_START_DESC),
        BotCommand("admin",  T.CMD_ADMIN_DESC),
        BotCommand("cancel", T.CMD_CANCEL_DESC),
    ])

    # 4. Start Supabase keep-alive background coroutine
    asyncio.ensure_future(db.ping_supabase())
    logger.info("Supabase keep-alive scheduled.")

    # 5. Schedule daily reminder jobs
    job_queue = application.job_queue
    if job_queue is None:
        logger.warning("JobQueue unavailable — automated reminders will not run.")
        return

    async def _payment_start_guard(ctx):
        cycle = db.get_billing_cycle()
        _, __, eth_day = to_ethiopian(now_eth())
        if eth_day == cycle["start"]:
            await send_payment_start_reminder(ctx)

    async def _one_day_guard(ctx):
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        days = eth_days_in_month(eth_year, eth_month)
        end  = effective_end_day(eth_year, eth_month, cycle["end"])
        one_before = end - 1 if end > 1 else days
        if eth_day == one_before:
            await send_one_day_reminder(ctx)

    async def _final_day_guard(ctx):
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        end = effective_end_day(eth_year, eth_month, cycle["end"])
        if eth_day == end:
            await send_final_day_reminder(ctx)

    async def _monthly_reset_guard(ctx):
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        days = eth_days_in_month(eth_year, eth_month)
        end  = effective_end_day(eth_year, eth_month, cycle["end"])
        reset_day = end + 1 if end < days else 1
        if eth_day == reset_day:
            await monthly_cycle_reset_job(ctx)

    noon          = dt_time(12, 0,  tzinfo=ETH_TZ)
    midnight_five = dt_time( 0, 5,  tzinfo=ETH_TZ)

    job_queue.run_daily(_payment_start_guard, time=noon,          name="payment_start")
    job_queue.run_daily(_one_day_guard,        time=noon,          name="one_day_reminder")
    job_queue.run_daily(_final_day_guard,      time=noon,          name="final_day_reminder")
    job_queue.run_daily(_monthly_reset_guard,  time=midnight_five, name="monthly_cycle_reset")

    logger.info("Automated reminder and monthly reset jobs scheduled.")


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
    app.add_handler(MessageHandler(
        filters.Regex(rf"^{T.BTN_PAY_RENEW}$"), pay_renew
    ))
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
