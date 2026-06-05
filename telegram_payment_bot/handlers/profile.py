"""
handlers/profile.py
────────────────────
User profile view + name edit + phone edit conversation.

FIXES:
 - format_eth_date() crash was upstream; calendar module is now fixed.
 - Phone display and phone-edit flow added.
 - No more duplicate handler registration with main.py.
"""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database.client as db
from keyboards.user_keyboards import contact_keyboard, main_menu_keyboard, profile_keyboard
from texts import T
from utils import format_eth_date

logger = logging.getLogger(__name__)

# Conversation states (local to this handler — unique within profile conv)
EDIT_NAME_INPUT  = 0
EDIT_PHONE_INPUT = 1


async def profile_callback(update: Update, context: CallbackContext) -> int:
    """
    Router for profile inline callbacks.
    - "profile_view"       → render the profile card
    - "profile_edit_name"  → prompt for new name (returns EDIT_NAME_INPUT)
    - "profile_edit_phone" → prompt for new phone (returns EDIT_PHONE_INPUT)
    """
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    user  = db.get_user(tg_id)

    if not user:
        await query.edit_message_text(T.PROFILE_NOT_FOUND, parse_mode="Markdown")
        return ConversationHandler.END

    if query.data == "profile_edit_name":
        await query.edit_message_text(T.EDIT_NAME_PROMPT, parse_mode="Markdown")
        return EDIT_NAME_INPUT

    if query.data == "profile_edit_phone":
        # Must send a NEW message — edit_message_text only accepts InlineKeyboardMarkup,
        # but contact_keyboard() is a ReplyKeyboardMarkup (the phone-share button).
        await query.message.reply_text(
            T.EDIT_PHONE_PROMPT,
            reply_markup=contact_keyboard(),
            parse_mode="Markdown",
        )
        return EDIT_PHONE_INPUT

    # Default: show profile card
    await _send_profile(query, user)
    return ConversationHandler.END


async def _send_profile(query, user: dict) -> None:
    """Render and send the profile card via an edit_message_text call."""
    joined_display = "—"
    if user.get("joined_at"):
        try:
            gd = datetime.fromisoformat(str(user["joined_at"]).replace("Z", "+00:00"))
            joined_display = format_eth_date(gd)   # converts GC datetime → Ethiopian display
        except Exception:
            joined_display = "—"   # never show raw GC date on failure

    status_icon = T.STATUS_PAID if user.get("status") == "paid" else T.STATUS_UNPAID
    phone_display = user.get("phone") or T.PROFILE_NO_PHONE

    text = T.PROFILE_TEXT.format(
        header     = T.PROFILE_HEADER,
        name_lbl   = T.PROFILE_NAME,
        name       = user["name"],
        phone_lbl  = T.PROFILE_PHONE_LBL,
        phone      = phone_display,
        id_lbl     = T.PROFILE_TG_ID,
        tg_id      = user["telegram_id"],
        status_lbl = T.PROFILE_STATUS,
        status     = status_icon,
        joined_lbl = T.PROFILE_JOINED,
        joined     = joined_display,
        eth_suffix = T.PROFILE_ETH_SUFFIX,
    )

    await query.edit_message_text(
        text,
        reply_markup=profile_keyboard(),
        parse_mode="Markdown",
    )


async def show_profile(update: Update, context: CallbackContext) -> None:
    """
    Called when the user taps the 'My Profile' reply-keyboard button.
    Sends a new message (not edit) with the profile card.
    """
    tg_id = update.effective_user.id
    user  = db.get_user(tg_id)

    if not user:
        await update.message.reply_text(T.PROFILE_NOT_FOUND, parse_mode="Markdown")
        return

    joined_display = "—"
    if user.get("joined_at"):
        try:
            gd = datetime.fromisoformat(str(user["joined_at"]).replace("Z", "+00:00"))
            joined_display = format_eth_date(gd)   # converts GC datetime → Ethiopian display
        except Exception:
            joined_display = "—"   # never show raw GC date on failure

    status_icon = T.STATUS_PAID if user.get("status") == "paid" else T.STATUS_UNPAID
    phone_display = user.get("phone") or T.PROFILE_NO_PHONE

    text = T.PROFILE_TEXT.format(
        header     = T.PROFILE_HEADER,
        name_lbl   = T.PROFILE_NAME,
        name       = user["name"],
        phone_lbl  = T.PROFILE_PHONE_LBL,
        phone      = phone_display,
        id_lbl     = T.PROFILE_TG_ID,
        tg_id      = user["telegram_id"],
        status_lbl = T.PROFILE_STATUS,
        status     = status_icon,
        joined_lbl = T.PROFILE_JOINED,
        joined     = joined_display,
        eth_suffix = T.PROFILE_ETH_SUFFIX,
    )

    await update.message.reply_text(
        text,
        reply_markup=profile_keyboard(),
        parse_mode="Markdown",
    )


# ── Edit name ─────────────────────────────────────────────────────────────────

async def receive_new_name(update: Update, context: CallbackContext) -> int:
    new_name = update.message.text.strip() if update.message.text else ""

    if not (2 <= len(new_name) <= 60):
        await update.message.reply_text(T.EDIT_NAME_TOO_SHORT, parse_mode="Markdown")
        return EDIT_NAME_INPUT

    db.update_user_name(update.effective_user.id, new_name)
    await update.message.reply_text(
        T.EDIT_NAME_SUCCESS.format(name=new_name),
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ── Edit phone ────────────────────────────────────────────────────────────────

async def receive_new_phone(update: Update, context: CallbackContext) -> int:
    phone = None

    if update.message.contact and update.message.contact.phone_number:
        phone = update.message.contact.phone_number
    elif update.message.text:
        txt = update.message.text.strip()
        if txt and (txt.startswith("+") or txt.isdigit()) and len(txt) >= 7:
            phone = txt

    if not phone:
        await update.message.reply_text(
            T.EDIT_PHONE_INVALID,
            reply_markup=contact_keyboard(),
            parse_mode="Markdown",
        )
        return EDIT_PHONE_INPUT

    db.update_user_phone(update.effective_user.id, phone)
    await update.message.reply_text(
        T.EDIT_PHONE_SUCCESS.format(phone=phone),
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ── Cancel helper ─────────────────────────────────────────────────────────────

async def cancel_profile(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        T.OPERATION_CANCELLED,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


def build_profile_conversation() -> ConversationHandler:
    """
    Build and return the profile ConversationHandler.
    Entry points: profile_edit_name and profile_edit_phone callbacks.
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(profile_callback, pattern=r"^profile_edit_name$"),
            CallbackQueryHandler(profile_callback, pattern=r"^profile_edit_phone$"),
        ],
        states={
            EDIT_NAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_name),
            ],
            EDIT_PHONE_INPUT: [
                MessageHandler(filters.CONTACT, receive_new_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_phone),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_profile)],
        allow_reentry=True,
        name="profile_edit",
        persistent=False,
    )
