"""
handlers/common.py
───────────────────
Shared handler utilities reused across user-facing handlers.
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from keyboards import main_menu_keyboard
from texts import T


async def cancel_user_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Universal /cancel handler — ends any active user conversation."""
    await update.message.reply_text(
        T.OPERATION_CANCELLED,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END
