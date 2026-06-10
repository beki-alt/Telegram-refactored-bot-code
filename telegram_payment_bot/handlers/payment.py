"""
handlers/payment.py
────────────────────
Payment submission flow (screenshot → forward to channel → admin review).

FIXES:
 - register_user() fallback path now uses default phone="" (BUG-01 fix).
 - Duplicate-payment guard added: aborts if a pending/approved payment exists
   for the current Ethiopian month.
 - receipt_file_id stored in the payments table so admins can view the photo.
"""

import logging

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
import database.client as db
from keyboards.user_keyboards import main_menu_keyboard, payment_confirm_keyboard
from texts import T
from utils import format_eth_date, format_eth_date_storage, now_eth, to_ethiopian

logger = logging.getLogger(__name__)

# Conversation states (local, unique within this handler)
SCREENSHOT_STATE  = 0
CONFIRM_STATE     = 1


async def pay_renew(update: Update, context: CallbackContext) -> int:
    """
    Entry: user taps 'ክፈል / አድስ' button.
    Checks payment status, shows bank info, and asks for receipt screenshot.
    """
    tg_user = update.effective_user

    # Ensure the user record exists (phone="" for legacy callers)
    user = db.get_user(tg_user.id)
    if not user:
        user = db.register_user(tg_user.id, tg_user.full_name, phone="", username=tg_user.username)

    # ── Duplicate-payment guard ──────────────────────────────────────────────
    eth_year, eth_month, _ = to_ethiopian(now_eth())

    if user.get("status") == "paid":
        await update.message.reply_text(
            T.PAYMENT_ALREADY_PAID,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    if db.has_pending_or_approved_payment(tg_user.id, eth_month, eth_year):
        await update.message.reply_text(
            T.PAYMENT_ALREADY_PENDING,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    # ── Show bank accounts ───────────────────────────────────────────────────
    banks = db.get_active_bank_accounts()
    if not banks:
        await update.message.reply_text(
            T.PAYMENT_NO_BANK,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    bank_text = T.PAYMENT_BANK_HEADER
    for b in banks:
        bank_text += T.PAYMENT_BANK_ROW.format(
            bank_name=b["bank_name"],
            account_number=b["account_number"],
            account_holder=b["account_holder"],
        )
    bank_text += T.PAYMENT_BANK_FOOTER

    await update.message.reply_text(bank_text, parse_mode="Markdown")
    return SCREENSHOT_STATE


async def receive_screenshot(update: Update, context: CallbackContext) -> int:
    """Receive the receipt photo. Store file_id and ask for confirmation."""
    if not update.message.photo:
        await update.message.reply_text(T.PAYMENT_PHOTO_ONLY, parse_mode="Markdown")
        return SCREENSHOT_STATE

    # Store the best-quality photo's file_id
    file_id = update.message.photo[-1].file_id
    context.user_data["receipt_file_id"] = file_id

    await update.message.reply_text(
        T.PAYMENT_SCREENSHOT_RECEIVED,
        reply_markup=payment_confirm_keyboard(),
        parse_mode="Markdown",
    )
    return CONFIRM_STATE


async def confirm_payment(update: Update, context: CallbackContext) -> int:
    """User confirms — forward receipt to channel and create payment record."""
    query = update.callback_query
    await query.answer()

    tg_user  = update.effective_user
    file_id  = context.user_data.get("receipt_file_id")

    if not file_id:
        await query.edit_message_text(T.PAYMENT_NO_PHOTO, parse_mode="Markdown")
        return ConversationHandler.END

    # ── Forward photo to receipt channel ────────────────────────────────────
    channel_id = config.RECEIPT_CHANNEL_ID
    if not channel_id:
        await query.edit_message_text(
            T.PAYMENT_NO_CHANNEL,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    now_dt         = now_eth()
    eth_year, eth_month, _ = to_ethiopian(now_dt)
    eth_date_str   = format_eth_date_storage(now_dt)
    eth_date_human = format_eth_date(now_dt)
    user           = db.get_user(tg_user.id)
    display_name   = user["name"] if user else tg_user.full_name

    caption = T.RECEIPT_CAPTION.format(
        name=display_name,
        tg_id=tg_user.id,
        eth_date=eth_date_human,
    )

    await query.edit_message_text(T.PAYMENT_SENDING, parse_mode="Markdown")

    try:
        sent = await context.bot.send_photo(
            chat_id=channel_id,
            photo=file_id,
            caption=caption,
            parse_mode="Markdown",
        )
        channel_msg_id = sent.message_id
    except Exception as exc:
        logger.error(f"Failed to send receipt to channel: {exc}")
        await query.edit_message_text(
            T.PAYMENT_SEND_FAILED,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    # ── Create payment record with file_id stored ────────────────────────────
    db.create_payment_record(
        telegram_id=tg_user.id,
        receipt_channel_msg_id=channel_msg_id,
        eth_month=eth_month,
        eth_year=eth_year,
        eth_payment_date=eth_date_str,
        receipt_file_id=file_id,
    )

    context.user_data.pop("receipt_file_id", None)

    await context.bot.send_message(
        chat_id=tg_user.id,
        text=T.PAYMENT_SUCCESS,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_payment(update: Update, context: CallbackContext) -> int:
    """User cancels via inline button."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("receipt_file_id", None)
    await query.edit_message_text(T.PAYMENT_CANCELLED, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel_command(update: Update, context: CallbackContext) -> int:
    """/cancel command during payment flow."""
    context.user_data.pop("receipt_file_id", None)
    await update.message.reply_text(
        T.OPERATION_CANCELLED,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


def build_payment_conversation() -> ConversationHandler:
    """Build and return the payment ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{T.BTN_PAY_RENEW}$"), pay_renew),
        ],
        states={
            SCREENSHOT_STATE: [
                MessageHandler(filters.PHOTO, receive_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_screenshot),
            ],
            CONFIRM_STATE: [
                CallbackQueryHandler(confirm_payment, pattern=r"^confirm_payment$"),
                CallbackQueryHandler(cancel_payment,  pattern=r"^cancel_payment$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        allow_reentry=True,
        name="payment",
        persistent=False,
    )
