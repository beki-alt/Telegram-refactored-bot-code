"""
handlers/profile.py
────────────────────
👤 My Profile — view and edit name / phone number.

Supports:
  • View profile: name, phone, Telegram ID, payment status, join date
  • Edit name   (inline button → text input)
  • Edit phone  (inline button → contact button → save)
"""

import logging
from datetime import datetime

from telegram import ReplyKeyboardRemove, Update
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
from keyboards.user_keyboards import (
    contact_keyboard,
    main_menu_keyboard,
    profile_keyboard,
)
from texts import T
from utils import format_eth_date

logger = logging.getLogger(__name__)

EDIT_NAME_INPUT  = 0
EDIT_PHONE_INPUT = 1


async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's full profile."""
    tg_user = update.effective_user
    user = db.get_user(tg_user.id) or db.register_user(
        telegram_id = tg_user.id,
        name        = tg_user.full_name or f"User {tg_user.id}",
        phone       = "",
        username    = tg_user.username,
    )

    status_display = T.STATUS_PAID if user.get("status") == "paid" else T.STATUS_UNPAID
    phone_display  = user.get("phone", "").strip() or T.PROFILE_NO_PHONE

    joined_raw = str(user.get("joined_at", ""))[:10]
    try:
        gd             = datetime.strptime(joined_raw, "%Y-%m-%d")
        joined_display = format_eth_date(gd)
    except Exception:
        joined_display = joined_raw

    text = T.PROFILE_TEXT.format(
        header     = T.PROFILE_HEADER,
        name_lbl   = T.PROFILE_NAME,
        name       = user["name"],
        phone_lbl  = T.PROFILE_PHONE,
        phone      = phone_display,
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
        parse_mode   = "Markdown",
        reply_markup = profile_keyboard(),
    )


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Edit Name / Edit Phone inline buttons."""
    query = update.callback_query
    await query.answer()

    if query.data == "profile_edit_name":
        await query.edit_message_text(T.EDIT_NAME_PROMPT, parse_mode="Markdown")
        return EDIT_NAME_INPUT

    if query.data == "profile_edit_phone":
        await query.edit_message_text(T.EDIT_PHONE_PROMPT, parse_mode="Markdown")
        # Send a new message with the contact keyboard (can't use inline for contacts)
        await query.message.reply_text(
            T.EDIT_PHONE_SHARE,
            reply_markup = contact_keyboard(),
        )
        return EDIT_PHONE_INPUT


# ── Edit name ─────────────────────────────────────────────────────────────────

async def receive_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text.strip()

    if len(new_name) < 2 or len(new_name) > 60:
        await update.message.reply_text(T.EDIT_NAME_TOO_SHORT)
        return EDIT_NAME_INPUT

    db.update_user_name(update.effective_user.id, new_name)
    await update.message.reply_text(
        T.EDIT_NAME_SUCCESS.format(name=new_name),
        parse_mode   = "Markdown",
        reply_markup = main_menu_keyboard(),
    )
    logger.info(f"User {update.effective_user.id} changed name → '{new_name}'.")
    return ConversationHandler.END


# ── Edit phone ────────────────────────────────────────────────────────────────

async def receive_new_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Accept a contact share or typed text for the new phone number."""
    tg_id   = update.effective_user.id
    contact = update.message.contact

    if contact:
        phone = contact.phone_number.strip()
    else:
        # Allow manually typed phone as fallback
        typed = update.message.text.strip()
        if not typed.lstrip("+").isdigit() or len(typed) < 7:
            await update.message.reply_text(
                T.EDIT_PHONE_INVALID,
                reply_markup = contact_keyboard(),
            )
            return EDIT_PHONE_INPUT
        phone = typed

    db.update_user_phone(tg_id, phone)
    await update.message.reply_text(
        T.EDIT_PHONE_SUCCESS.format(phone=phone),
        parse_mode   = "Markdown",
        reply_markup = ReplyKeyboardRemove(),
    )
    await update.message.reply_text(T.BACK_TO_MENU, reply_markup=main_menu_keyboard())
    logger.info(f"User {tg_id} updated phone → {phone}.")
    return ConversationHandler.END


# ── ConversationHandler ───────────────────────────────────────────────────────

def build_profile_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                profile_callback,
                pattern=r"^profile_edit_(name|phone)$",
            ),
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
        fallbacks=[CommandHandler("cancel", cancel_user_conv)],
        allow_reentry=True,
    )
