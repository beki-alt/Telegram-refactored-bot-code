"""
main.py
────────
Application entry point.

Responsibilities:
  1. Initialize logging and configuration
  2. Seed the database with default settings
  3. Register all Telegram handlers
  4. Schedule automated billing reminder jobs
  5. Start the keep-alive Flask server
  6. Start polling for updates
"""

import asyncio
import logging
import os
from datetime import time as dt_time

from telegram import BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
import database as db
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
    build_support_conversation,
    my_profile,
    payment_schedule,
    profile_callback,
    start,
    support_and_history,
    support_history_callback,
    unknown_text,
)
from keep_alive import keep_alive
from texts import T
from utils import ETH_TZ, eth_days_in_month, now_eth, to_ethiopian

config.setup_logging()
logger = logging.getLogger(__name__)


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

    # Payment-start reminder: fires at noon, only on the billing start day
    async def _payment_start_guard(ctx):
        cycle = db.get_billing_cycle()
        _, __, eth_day = to_ethiopian(now_eth())
        if eth_day == cycle["start"]:
            await send_payment_start_reminder(ctx)

    # One-day-before reminder: fires at noon, one day before end day
    async def _one_day_guard(ctx):
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        days = eth_days_in_month(eth_year, eth_month)
        one_before = cycle["end"] - 1 if cycle["end"] > 1 else days
        if eth_day == one_before:
            await send_one_day_reminder(ctx)

    # Final-day reminder: fires at noon on the billing end day
    async def _final_day_guard(ctx):
        cycle = db.get_billing_cycle()
        _, __, eth_day = to_ethiopian(now_eth())
        if eth_day == cycle["end"]:
            await send_final_day_reminder(ctx)

    # Monthly reset: fires at 00:05 the day AFTER the end day
    async def _monthly_reset_guard(ctx):
        cycle = db.get_billing_cycle()
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        days = eth_days_in_month(eth_year, eth_month)
        reset_day = cycle["end"] + 1 if cycle["end"] < days else 1
        if eth_day == reset_day:
            await monthly_cycle_reset_job(ctx)

    noon = dt_time(12, 0, tzinfo=ETH_TZ)
    midnight_five = dt_time(0, 5, tzinfo=ETH_TZ)

    job_queue.run_daily(_payment_start_guard, time=noon,         name="payment_start")
    job_queue.run_daily(_one_day_guard,       time=noon,         name="one_day_reminder")
    job_queue.run_daily(_final_day_guard,     time=noon,         name="final_day_reminder")
    job_queue.run_daily(_monthly_reset_guard, time=midnight_five, name="monthly_cycle_reset")

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

    # ── Admin conversation (highest priority — catches admin callbacks first) ──
    app.add_handler(build_admin_conversation())

    # ── User conversations ────────────────────────────────────────────────────
    app.add_handler(build_profile_conversation())
    app.add_handler(build_payment_conversation())
    app.add_handler(build_support_conversation())

    # ── Core commands ─────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start))

    # ── Main menu reply-keyboard buttons ──────────────────────────────────────
    app.add_handler(MessageHandler(filters.Regex(rf"^{T.BTN_MY_PROFILE}$"), my_profile))
    app.add_handler(MessageHandler(filters.Regex(rf"^{T.BTN_SCHEDULE}$"),   payment_schedule))
    app.add_handler(MessageHandler(filters.Regex(rf"^{T.BTN_SUPPORT}$"),    support_and_history))

    # ── Fallback inline callbacks (outside active conversations) ─────────────
    app.add_handler(CallbackQueryHandler(profile_callback,       pattern=r"^profile_edit_name$"))
    app.add_handler(CallbackQueryHandler(support_history_callback, pattern=r"^(history_view|support_contact)$"))

    # ── Unknown text catch-all ────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))

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
