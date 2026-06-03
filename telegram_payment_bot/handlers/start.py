"""
handlers/start.py
──────────────────
/start command and unknown text fallback.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from keyboards import main_menu_keyboard
from texts import T

logger = logging.getLogger(__name__)

REGISTER_NAME = 0
REGISTER_PHONE = 1
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Register the user (idempotent) and show the main menu."""
    tg_user = update.effective_user
    user    = db.register_user(tg_user.id, tg_user.full_name)
    name    = user.get("name", tg_user.full_name)

    await update.message.reply_text(
        T.WELCOME.format(name=name),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    logger.info(f"User {tg_user.id} ({name}) started the bot.")


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all for unrecognized text messages."""
    await update.message.reply_text(T.UNKNOWN_COMMAND)
