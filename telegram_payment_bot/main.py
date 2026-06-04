"""
main.py
────────
Production entry point for the Telegram Payment Bot.

Startup sequence:
  1. Setup logging
  2. Validate config (warn on missing optionals, fail on missing required)
  3. Connect Supabase and seed default settings
  4. Seed super-admin if ADMIN_ID is set
  5. Register handlers
  6. Start APScheduler (billing reminders on Ethiopian calendar days)
  7. Phase 7: check_missed_jobs() — recover any reminders that were missed
     while the bot was offline
  8. Start Flask keep-alive server (Replit UptimeRobot pings)
  9. Start bot polling

All times are Africa/Addis_Ababa (Ethiopian time).
"""

import asyncio
import logging
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
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
from admin import (
    admin_panel,
    build_admin_conversation,
    check_missed_jobs,
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
    my_profile,
    payment_schedule,
    start,
    support_and_history,
    unknown_text,
)
from keep_alive import keep_alive
from texts import T
from utils import ETH_TZ, now_eth, to_ethiopian

logger = logging.getLogger(__name__)


# ── Scheduler setup ───────────────────────────────────────────────────────────

def _get_billing_days():
    """Return (start_day, end_day) from the DB for scheduler job calculations."""
    cycle    = db.get_billing_cycle()
    one_day  = cycle["end"] - 1 if cycle["end"] > 1 else 28
    reset    = cycle["end"] + 1 if cycle["end"] < 30 else 1
    return cycle["start"], cycle["end"], one_day, reset


def _build_scheduler(application: Application) -> AsyncIOScheduler:
    """
    Build the APScheduler with Ethiopian-time cron triggers.

    Jobs run daily at 08:00 Africa/Addis_Ababa. Each job checks internally
    whether the current Ethiopian day matches its trigger condition.
    This approach tolerates APScheduler's lack of Ethiopian calendar support.
    """
    scheduler = AsyncIOScheduler(timezone=ETH_TZ)

    async def _safe_payment_start():
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        cycle = db.get_billing_cycle()
        if eth_day == cycle["start"]:
            await send_payment_start_reminder(application.bot)

    async def _safe_one_day():
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        cycle = db.get_billing_cycle()
        trigger = cycle["end"] - 1 if cycle["end"] > 1 else 30
        if eth_day == trigger:
            await send_one_day_reminder(application.bot)

    async def _safe_final_day():
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        cycle = db.get_billing_cycle()
        if eth_day == cycle["end"]:
            await send_final_day_reminder(application.bot)

    async def _safe_monthly_reset():
        eth_year, eth_month, eth_day = to_ethiopian(now_eth())
        cycle = db.get_billing_cycle()
        reset_day = (cycle["end"] % 30) + 1
        if eth_day == reset_day:
            await monthly_cycle_reset_job(application.bot)

    # Run daily at 08:00 Addis Ababa time; each job self-checks the day
    scheduler.add_job(_safe_payment_start, CronTrigger(hour=8, minute=0, timezone=ETH_TZ), id="payment_start")
    scheduler.add_job(_safe_one_day,       CronTrigger(hour=8, minute=5, timezone=ETH_TZ), id="one_day")
    scheduler.add_job(_safe_final_day,     CronTrigger(hour=8, minute=10, timezone=ETH_TZ), id="final_day")
    scheduler.add_job(_safe_monthly_reset, CronTrigger(hour=9, minute=0,  timezone=ETH_TZ), id="monthly_reset")

    return scheduler


# ── Telegram bot commands ─────────────────────────────────────────────────────

async def _set_bot_commands(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("start",  T.CMD_START_DESC),
        BotCommand("admin",  T.CMD_ADMIN_DESC),
        BotCommand("cancel", T.CMD_CANCEL_DESC),
    ])
    logger.info("Bot commands registered.")


# ── Application builder ───────────────────────────────────────────────────────

def build_application() -> Application:
    application = (
        ApplicationBuilder()
        .token(config.TELEGRAM_TOKEN)
        .build()
    )

    # ── User handlers ─────────────────────────────────────────────────────────
    # /start is a ConversationHandler: greet → ask phone → save → main menu
    application.add_handler(build_start_conversation())

    # Conversation handlers (order matters — most specific first)
    application.add_handler(build_payment_conversation())
    application.add_handler(build_profile_conversation())
    application.add_handler(build_support_conversation())

    # Non-conversation message handlers
    application.add_handler(
        MessageHandler(filters.Regex(rf"^{T.BTN_MY_PROFILE}$"), my_profile)
    )
    application.add_handler(
        MessageHandler(filters.Regex(rf"^{T.BTN_SCHEDULE}$"), payment_schedule)
    )
    application.add_handler(
        MessageHandler(filters.Regex(rf"^{T.BTN_SUPPORT}$"), support_and_history)
    )

    # ── Admin handlers ────────────────────────────────────────────────────────
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(build_admin_conversation())

    # ── Catch-all ─────────────────────────────────────────────────────────────
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text)
    )

    return application


# ── Startup / shutdown hooks ──────────────────────────────────────────────────

async def _on_startup(application: Application) -> None:
    logger.info("Bot starting up...")

    # Seed default settings (idempotent)
    db.init_tables()

    # Seed super admin
    if config.ADMIN_ID:
        db.add_admin(config.ADMIN_ID, added_by=config.ADMIN_ID, is_super=True)
        logger.info(f"Super admin seeded: {config.ADMIN_ID}")

    # Register bot commands
    await _set_bot_commands(application)

    # Phase 7: check for missed reminder jobs
    try:
        await check_missed_jobs(application.bot)
    except Exception as exc:
        logger.error(f"Missed-job recovery failed: {exc}")

    # Start APScheduler
    scheduler = _build_scheduler(application)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Scheduler started.")

    # Start keep-alive Flask server
    keep_alive()

    # Start Supabase keep-alive ping in background
    asyncio.create_task(db.ping_supabase())

    logger.info("Bot startup complete.")


async def _on_shutdown(application: Application) -> None:
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    config.setup_logging()
    config.validate()

    logger.info("Initialising Telegram Payment Bot...")

    application = build_application()
    application.post_init    = _on_startup
    application.post_shutdown = _on_shutdown

    logger.info("Starting polling...")
    application.run_polling(
        allowed_updates=["message", "callback_query", "edited_message"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as exc:
        logger.critical(f"Fatal startup error: {exc}", exc_info=True)
        sys.exit(1)
