"""
handlers/start.py
──────────────────
/start command — registration flow with phone number collection.

Flow:
  1. User sends /start
  2. If already registered WITH a phone → show main menu immediately
  3. If new user OR phone is missing → greet + ask to share phone via button
  4. User presses "Share Phone" button → contact message arrives
  5. Bot saves phone, confirms, shows main menu

Re-running /start (existing user with phone) is always safe — it just
shows the main menu again without asking for phone a second time.
"""

import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
from keyboards.user_keyboards import contact_keyboard, main_menu_keyboard
from texts import T

logger = logging.getLogger(__name__)

START_AWAITING_PHONE = 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entry point for /start.
    • New user or user without phone → ask for phone number via button.
    • Existing user with phone       → show main menu directly.
    """
    tg_user = update.effective_user

    # Register idempotently (no phone yet — will be completed after sharing)
    user = db.register_user(
        telegram_id = tg_user.id,
        name        = tg_user.full_name or f"User {tg_user.id}",
        phone       = "",
        username    = tg_user.username,
    )

    # If user already has a phone number, skip straight to main menu
    if user.get("phone", "").strip():
        await update.message.reply_text(
            T.WELCOME.format(name=user["name"]),
            parse_mode   = "Markdown",
            reply_markup = main_menu_keyboard(),
        )
        logger.info(f"Returning user {tg_user.id} started bot (phone already on file).")
        return ConversationHandler.END

    # New user (or phone missing) — ask to share phone
    await update.message.reply_text(
        T.ASK_PHONE.format(name=user["name"]),
        parse_mode   = "Markdown",
        reply_markup = contact_keyboard(),
    )
    logger.info(f"New user {tg_user.id} — requesting phone number.")
    return START_AWAITING_PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receive the shared contact, save phone, show main menu.
    Telegram sends phone numbers via a Contact object, not as plain text.
    """
    tg_user = update.effective_user
    contact = update.message.contact

    if contact is None:
        # User typed text instead of pressing the button
        await update.message.reply_text(
            T.ASK_PHONE_BUTTON_ONLY,
            reply_markup = contact_keyboard(),
        )
        return START_AWAITING_PHONE

    # Normalise: strip leading '+' so storage is consistent
    phone = contact.phone_number.strip()

    db.update_user_phone(tg_user.id, phone)
    user = db.get_user(tg_user.id)
    name = user["name"] if user else tg_user.full_name

    await update.message.reply_text(
        T.PHONE_RECEIVED.format(name=name, phone=phone),
        parse_mode   = "Markdown",
        reply_markup = ReplyKeyboardRemove(),
    )
    # Small pause then show main menu
    await update.message.reply_text(
        T.WELCOME.format(name=name),
        parse_mode   = "Markdown",
        reply_markup = main_menu_keyboard(),
    )
    logger.info(f"User {tg_user.id} registered phone: {phone}")
    return ConversationHandler.END


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all for unrecognized text messages."""
    await update.message.reply_text(T.UNKNOWN_COMMAND)


def build_start_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_AWAITING_PHONE: [
                # Contact button press
                MessageHandler(filters.CONTACT, receive_phone),
                # Typed text when button is expected
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone),
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        allow_reentry=True,
        # Don't block other handlers while waiting for phone
        per_chat=True,
        per_user=True,
        per_message=False,
    )


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        T.OPERATION_CANCELLED,
        parse_mode   = "Markdown",
        reply_markup = main_menu_keyboard(),
    )
    return ConversationHandler.END
