"""
handlers/profile.py
────────────────────
👤 My Profile — view and edit user account information.

Card system has been REMOVED. Users can only:
  - View their profile info
  - Edit their display name
"""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
from handlers.common import cancel_user_conv
from keyboards.user_keyboards import main_menu_keyboard, profile_keyboard
from texts import T
from utils import ETH_TZ, format_eth_date

logger = logging.getLogger(__name__)

# ── Conversation state ────────────────────────────────────────────────────────
EDIT_NAME_INPUT = 0


# ── Handlers ──────────────────────────────────────────────────────────────────

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's profile information."""
    tg_user = update.effective_user
    user    = db.get_user(tg_user.id) or db.register_user(tg_user.id, tg_user.full_name)

    status_display = T.STATUS_PAID if user["status"] == "paid" else T.STATUS_UNPAID

    # Format join date as Ethiopian calendar
    joined_raw = str(user.get("joined_at", ""))[:10]
    try:
        gd = datetime.strptime(joined_raw, "%Y-%m-%d")
        joined_display = format_eth_date(gd)
    except Exception:
        joined_display = joined_raw

    text = T.PROFILE_TEXT.format(
        header     = T.PROFILE_HEADER,
        name_lbl   = T.PROFILE_NAME,
        name       = user["name"],
        id_lbl     = T.PROFILE_TG_ID,
        tg_id      = user["telegram_id"],
        status_lbl = T.PROFILE_STATUS,
        status     = status_display,
        joined_lbl = T.PROFILE_JOINED,
        joined     = joined_display,
        eth_suffix = T.PROFILE_ETH_SUFFIX,
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=profile_keyboard(),
    )


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks from the profile view."""
    query = update.callback_query
    await query.answer()

    if query.data == "profile_edit_name":
        await query.edit_message_text(T.EDIT_NAME_PROMPT, parse_mode="Markdown")
        return EDIT_NAME_INPUT


async def receive_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the user's new display name."""
    new_name = update.message.text.strip()

    if len(new_name) < 2 or len(new_name) > 60:
        await update.message.reply_text(T.EDIT_NAME_TOO_SHORT)
        return EDIT_NAME_INPUT

    db.update_user_name(update.effective_user.id, new_name)
    await update.message.reply_text(
        T.EDIT_NAME_SUCCESS.format(name=new_name),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    logger.info(f"User {update.effective_user.id} changed name to '{new_name}'.")
    return ConversationHandler.END


# ── Conversation builder ──────────────────────────────────────────────────────

def build_profile_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(profile_callback, pattern=r"^profile_edit_name$"),
        ],
        states={
            EDIT_NAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_user_conv)],
        allow_reentry=True,
    )
