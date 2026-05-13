"""
handlers/payment.py
────────────────────
💳 Pay / Renew — payment screenshot submission workflow.
📅 Payment Schedule — billing cycle countdown display.

Workflow:
  1. User taps "ክፈል / አድስ"
  2. Bot shows bank account details
  3. User uploads a payment screenshot (photo)
  4. User confirms to send to admin channel
  5. Bot forwards to channel, creates pending payment record
  6. Admin reviews from inbox
"""

import logging
import traceback

import config
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
from keyboards.user_keyboards import main_menu_keyboard, payment_confirm_keyboard
from texts import T
from utils import (
    ETH_TZ,
    eth_days_in_month,
    eth_month_name,
    format_eth_date,
    format_eth_date_storage,
    now_eth,
    to_ethiopian,
)

logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────────────────
PAYMENT_AWAITING_SCREENSHOT = 0
PAYMENT_CONFIRM             = 1


def _resolve_receipt_chat_id():
    """Parse CHANNEL_ID to int. Returns None if unset or invalid."""
    raw = config.CHANNEL_ID
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.error(f"CHANNEL_ID '{raw}' is not a valid integer.")
        return None


# ── Handlers ──────────────────────────────────────────────────────────────────

async def pay_renew(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: show bank accounts or notify if already paid."""
    tg_user = update.effective_user
    user    = db.get_user(tg_user.id) or db.register_user(tg_user.id, tg_user.full_name)

    if user["status"] == "paid":
        await update.message.reply_text(T.PAYMENT_ALREADY_PAID, parse_mode="Markdown")
        return ConversationHandler.END

    accounts = db.get_active_bank_accounts()
    if not accounts:
        await update.message.reply_text(T.PAYMENT_NO_BANK, parse_mode="Markdown")
        return ConversationHandler.END

    bank_text = T.PAYMENT_BANK_HEADER
    for a in accounts:
        bank_text += T.PAYMENT_BANK_ROW.format(
            bank_name      = a["bank_name"],
            account_number = a["account_number"],
            account_holder = a["account_holder"],
        )
    bank_text += T.PAYMENT_BANK_FOOTER

    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        bank_text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PAYMENT_AWAITING_SCREENSHOT


async def receive_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the receipt photo and ask for confirmation."""
    if not update.message.photo:
        await update.message.reply_text(T.PAYMENT_PHOTO_ONLY, parse_mode="Markdown")
        return PAYMENT_AWAITING_SCREENSHOT

    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text(T.PROFILE_NOT_FOUND)
        return ConversationHandler.END

    context.user_data["receipt_file_id"] = update.message.photo[-1].file_id

    await update.message.reply_text(
        T.PAYMENT_SCREENSHOT_RECEIVED,
        parse_mode="Markdown",
        reply_markup=payment_confirm_keyboard(),
    )
    return PAYMENT_CONFIRM


async def confirm_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User confirms or cancels sending the receipt to admins."""
    query = update.callback_query
    await query.answer()
    data  = query.data
    tg_id = query.from_user.id

    if data == "cancel_payment":
        await query.edit_message_text(T.PAYMENT_CANCELLED, parse_mode="Markdown")
        await query.message.reply_text(T.BACK_TO_MENU, reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if data == "confirm_payment":
        receipt_chat_id = _resolve_receipt_chat_id()
        if receipt_chat_id is None:
            await query.edit_message_text(T.PAYMENT_NO_CHANNEL, parse_mode="Markdown")
            return ConversationHandler.END

        file_id = context.user_data.get("receipt_file_id")
        if not file_id:
            await query.edit_message_text(T.PAYMENT_NO_PHOTO)
            return ConversationHandler.END

        await query.edit_message_text(T.PAYMENT_SENDING)

        user     = db.get_user(tg_id)
        now_dt   = now_eth()
        eth_date = format_eth_date(now_dt)

        try:
            forwarded = await query.get_bot().send_photo(
                chat_id=receipt_chat_id,
                photo=file_id,
                caption=T.RECEIPT_CAPTION.format(
                    name     = user["name"] if user else str(tg_id),
                    tg_id    = tg_id,
                    eth_date = eth_date,
                ),
                parse_mode="Markdown",
            )
            channel_msg_id = forwarded.message_id
        except Exception:
            logger.error(f"Failed to forward receipt for user {tg_id}:\n{traceback.format_exc()}")
            await query.edit_message_text(T.PAYMENT_SEND_FAILED, parse_mode="Markdown")
            return ConversationHandler.END

        eth_year, eth_month, _ = to_ethiopian(now_dt)
        db.create_payment_record(
            telegram_id            = tg_id,
            receipt_channel_msg_id = channel_msg_id,
            eth_month              = eth_month,
            eth_year               = eth_year,
            eth_payment_date       = format_eth_date_storage(now_dt),
        )

        await query.edit_message_text(T.PAYMENT_SUCCESS, parse_mode="Markdown")
        await query.message.reply_text(T.BACK_TO_MENU, reply_markup=main_menu_keyboard())
        logger.info(f"User {tg_id} submitted payment receipt (channel msg {channel_msg_id}).")
        return ConversationHandler.END


# ── Payment schedule ──────────────────────────────────────────────────────────

async def payment_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current billing cycle countdown in Ethiopian calendar."""
    cycle   = db.get_billing_cycle()
    now_dt  = now_eth()
    eth_year, eth_month, eth_day = to_ethiopian(now_dt)
    today   = eth_day
    start   = cycle["start"]
    end     = cycle["end"]
    days_in_month = eth_days_in_month(eth_year, eth_month)

    in_billing_period = False
    days_remaining    = 0
    next_event        = ""

    if today >= start:
        in_billing_period = True
        if end < start:
            days_remaining = (days_in_month - today) + end
        else:
            days_remaining = end - today
        next_event = T.SCHEDULE_NEXT_END.format(end=end)
    elif today <= end and end < start:
        in_billing_period = True
        days_remaining    = end - today
        next_event        = T.SCHEDULE_NEXT_END.format(end=end)
    else:
        days_remaining = start - today
        next_event     = T.SCHEDULE_NEXT_START.format(start=start)

    user        = db.get_user(update.effective_user.id)
    user_status = T.STATUS_PAID if user and user["status"] == "paid" else T.STATUS_UNPAID

    if in_billing_period:
        if days_remaining > 1:
            countdown = T.SCHEDULE_DAYS_LEFT.format(days=days_remaining)
        elif days_remaining == 1:
            countdown = T.SCHEDULE_ONE_DAY_LEFT
        else:
            countdown = T.SCHEDULE_LAST_DAY
    else:
        countdown = T.SCHEDULE_DAYS_TO_START.format(days=days_remaining)

    text = (
        f"{T.SCHEDULE_HEADER}\n\n"
        f"{T.SCHEDULE_MONTH.format(month_name=eth_month_name(eth_month), year=eth_year)}\n"
        f"{T.SCHEDULE_CYCLE.format(start=start, end=end)}\n\n"
        f"{T.SCHEDULE_DIVIDER}\n"
        f"{countdown}\n"
        f"{T.SCHEDULE_NEXT.format(event=next_event)}\n\n"
        f"{T.SCHEDULE_DIVIDER}\n"
        f"{T.SCHEDULE_USER_STATUS.format(status=user_status)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Conversation builder ──────────────────────────────────────────────────────

def build_payment_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(rf"^{T.BTN_PAY_RENEW}$"), pay_renew),
        ],
        states={
            PAYMENT_AWAITING_SCREENSHOT: [
                MessageHandler(filters.PHOTO, receive_payment_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_screenshot),
            ],
            PAYMENT_CONFIRM: [
                CallbackQueryHandler(
                    confirm_payment_callback,
                    pattern=r"^(confirm_payment|cancel_payment)$",
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_user_conv)],
        allow_reentry=True,
    )
