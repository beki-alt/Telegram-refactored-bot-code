"""
handlers/start.py
──────────────────
/start command handler with multi-step phone collection for new users.

FIXES:
 - register_user() no longer called with missing phone argument.
 - New users go through a ConversationHandler (REGISTER_PHONE state) that
   asks for phone via a contact-share button, saves it, then shows main menu.
 - Existing users are greeted directly and shown the main menu.
"""

import logging

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database.client as db
from keyboards.user_keyboards import contact_keyboard, main_menu_keyboard
from texts import T

logger = logging.getLogger(__name__)

# Conversation state
REGISTER_PHONE = 0


async def start(update: Update, context: CallbackContext) -> int:
    """
    Entry point for /start.
    - Existing user → greet + show main menu (END conversation immediately).
    - New user → ask for phone number via contact button.
    """
    tg_user = update.effective_user
    user = db.get_user(tg_user.id)

    if user:
        # User already registered — just show main menu
        await update.message.reply_text(
            T.WELCOME.format(name=user["name"]),
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    # New user — store Telegram info and ask for phone
    context.user_data["reg_name"]     = tg_user.full_name or "ያልታወቀ"
    context.user_data["reg_username"] = tg_user.username

    await update.message.reply_text(
        T.REGISTER_WELCOME_NEW.format(name=tg_user.first_name or tg_user.full_name),
        reply_markup=contact_keyboard(),
        parse_mode="Markdown",
    )
    return REGISTER_PHONE


async def receive_phone(update: Update, context: CallbackContext) -> int:
    """
    Handles the phone contact share (or text fallback).
    Completes registration and shows the main menu.
    """
    phone = None

    if update.message.contact and update.message.contact.phone_number:
        phone = update.message.contact.phone_number
    elif update.message.text:
        txt = update.message.text.strip()
        # Accept typed phone numbers too (e.g. +251912345678)
        if txt and (txt.startswith("+") or txt.isdigit()) and len(txt) >= 7:
            phone = txt

    if not phone:
        await update.message.reply_text(
            T.REGISTER_PHONE_INVALID,
            reply_markup=contact_keyboard(),
            parse_mode="Markdown",
        )
        return REGISTER_PHONE

    name     = context.user_data.get("reg_name",     update.effective_user.full_name or "ያልታወቀ")
    username = context.user_data.get("reg_username", update.effective_user.username)

    db.complete_user_registration(
        telegram_id=update.effective_user.id,
        name=name,
        phone=phone,
        username=username,
    )

    logger.info(f"New user registered: {update.effective_user.id} ({name}), phone: {phone}")

    await update.message.reply_text(
        T.REGISTER_SUCCESS + T.WELCOME.format(name=name),
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def handle_unknown(update: Update, context: CallbackContext) -> None:
    """Catch-all for unrecognized text from users who are already registered."""
    await update.message.reply_text(
        T.UNKNOWN_COMMAND,
        reply_markup=main_menu_keyboard(),
    )


def build_start_conversation() -> ConversationHandler:
    """
    Returns the ConversationHandler for the /start command + phone registration.
    Register this BEFORE any other handlers in main.py.
    """
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER_PHONE: [
                MessageHandler(filters.CONTACT, receive_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
        name="start_registration",
        persistent=False,
    )
