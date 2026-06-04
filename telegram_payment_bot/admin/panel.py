"""
admin/panel.py
───────────────
/admin command — entry point for the admin panel.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from keyboards.admin_keyboards import admin_main_menu_keyboard
from middleware import admin_required
from texts import T

logger = logging.getLogger(__name__)


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the admin main menu."""
    total = db.get_total_users_count()
    paid  = db.get_total_paid_this_month()

    text = T.ADMIN_PANEL_HEADER.format(total=total, paid=paid)
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_main_menu_keyboard(),
    )


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'back to admin panel' callback."""
    query = update.callback_query
    await query.answer()

    total = db.get_total_users_count()
    paid  = db.get_total_paid_this_month()
    text  = T.ADMIN_PANEL_HEADER.format(total=total, paid=paid)

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_main_menu_keyboard(),
    )


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any active admin conversation."""
    if update.message:
        await update.message.reply_text(T.OPERATION_CANCELLED, parse_mode="Markdown")
    return ConversationHandler.END
