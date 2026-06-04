"""
admin/panel.py
───────────────
Admin panel entry point and top-level navigation callbacks.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database.client as db
from keyboards.admin_keyboards import admin_main_menu_keyboard
from middleware import admin_required
from texts import T

logger = logging.getLogger(__name__)


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the admin main panel. Entry point via /admin command."""
    total = db.get_total_users_count()
    paid  = db.get_total_paid_this_month()
    text  = T.ADMIN_PANEL_HEADER.format(total=total, paid=paid)
    await update.effective_message.reply_text(
        text,
        reply_markup=admin_main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route top-level admin navigation callbacks (back button only)."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "adm_back":
        total = db.get_total_users_count()
        paid  = db.get_total_paid_this_month()
        await query.edit_message_text(
            T.ADMIN_PANEL_HEADER.format(total=total, paid=paid),
            reply_markup=admin_main_menu_keyboard(),
            parse_mode="Markdown",
        )


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin /cancel — end any active admin conversation."""
    await update.message.reply_text(T.OPERATION_CANCELLED, parse_mode="Markdown")
    return ConversationHandler.END
