"""
admin/settings.py
──────────────────
System settings — message templates, notification toggles,
billing cycle (Phase 5: button-based), bank accounts.

Phase 5 fix: billing cycle day selection is now button-based (no text input).
  The admin sees a 6×5 grid of day buttons (1–30) with ✅ on the current day.

Phase 6 fix: after saving a new billing start day, if today == new start day,
  the admin is prompted to send the payment-start notification immediately.

Bug fix: state integers now come from admin/states.py (unique per module).
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from admin.states import (
    ADM_EDIT_MSG_TEXT,
    ADM_BILLING_PICK_START,
    ADM_BILLING_PICK_END,
    ADM_BILLING_CONFIRM_TRIGGER,
    ADM_ADD_BANK_NAME,
    ADM_ADD_BANK_ACCT,
    ADM_ADD_BANK_HOLDER,
)
from keyboards.admin_keyboards import (
    bank_keyboard,
    billing_cycle_keyboard,
    billing_trigger_keyboard,
    day_picker_keyboard,
    edit_messages_keyboard,
    notify_toggle_keyboard,
    settings_keyboard,
)
from middleware import admin_required
from texts import EDITABLE_MESSAGES, NOTIFICATION_KEYS, T
from utils import now_eth, to_ethiopian

logger = logging.getLogger(__name__)

# Re-export for admin/__init__.py compatibility
EDIT_MSG_TEXT        = ADM_EDIT_MSG_TEXT
SET_BILLING_START    = ADM_BILLING_PICK_START
SET_BILLING_END      = ADM_BILLING_PICK_END
ADD_BANK_NAME        = ADM_ADD_BANK_NAME
ADD_BANK_ACCT        = ADM_ADD_BANK_ACCT
ADD_BANK_HOLDER      = ADM_ADD_BANK_HOLDER


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Master handler for all settings sub-menu callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    # ── Main settings menu ──────────────────────────────────────────────────
    if data == "adm_settings":
        await query.edit_message_text(
            T.SETTINGS_HEADER,
            parse_mode="Markdown",
            reply_markup=settings_keyboard(),
        )
        return ConversationHandler.END

    # ── Edit message templates ───────────────────────────────────────────────
    if data == "adm_edit_msgs":
        await query.edit_message_text(
            T.EDIT_MSG_HEADER,
            parse_mode="Markdown",
            reply_markup=edit_messages_keyboard(EDITABLE_MESSAGES),
        )
        return ConversationHandler.END

    if data.startswith("edit_msg_"):
        key = data[len("edit_msg_"):]
        if key not in EDITABLE_MESSAGES:
            return ConversationHandler.END
        current = db.get_setting(key, "")
        label   = EDITABLE_MESSAGES[key]
        context.user_data["editing_msg_key"]   = key
        context.user_data["editing_msg_label"] = label
        await query.edit_message_text(
            T.EDIT_MSG_PROMPT.format(label=label, current=current or "_(ባዶ)_"),
            parse_mode="Markdown",
        )
        return ADM_EDIT_MSG_TEXT

    # ── Notification toggles ─────────────────────────────────────────────────
    if data == "adm_notify_toggle":
        await query.edit_message_text(
            T.NOTIFY_HEADER,
            parse_mode="Markdown",
            reply_markup=notify_toggle_keyboard(NOTIFICATION_KEYS, db.get_setting),
        )
        return ConversationHandler.END

    if data.startswith("toggle_"):
        key     = data[len("toggle_"):]
        current = db.get_setting(key, "true")
        new_val = "false" if current == "true" else "true"
        db.set_setting(key, new_val)
        # Refresh the toggle menu
        await query.edit_message_text(
            T.NOTIFY_HEADER,
            parse_mode="Markdown",
            reply_markup=notify_toggle_keyboard(NOTIFICATION_KEYS, db.get_setting),
        )
        return ConversationHandler.END

    # ── Billing cycle ────────────────────────────────────────────────────────
    if data == "adm_billing_cycle":
        cycle = db.get_billing_cycle()
        await query.edit_message_text(
            T.BILLING_CYCLE_HEADER.format(start=cycle["start"], end=cycle["end"]),
            parse_mode="Markdown",
            reply_markup=billing_cycle_keyboard(),
        )
        return ConversationHandler.END

    # Phase 5: show day picker for start day
    if data == "set_bill_start":
        cycle       = db.get_billing_cycle()
        current_day = cycle["start"]
        await query.edit_message_text(
            T.BILLING_PICK_START_HEADER.format(current=current_day),
            parse_mode="Markdown",
            reply_markup=day_picker_keyboard(
                callback_prefix="bill_start_day",
                current_day=current_day,
            ),
        )
        return ADM_BILLING_PICK_START

    # Phase 5: show day picker for end day
    if data == "set_bill_end":
        cycle       = db.get_billing_cycle()
        current_day = cycle["end"]
        await query.edit_message_text(
            T.BILLING_PICK_END_HEADER.format(current=current_day),
            parse_mode="Markdown",
            reply_markup=day_picker_keyboard(
                callback_prefix="bill_end_day",
                current_day=current_day,
            ),
        )
        return ADM_BILLING_PICK_END

    # Phase 6: immediate trigger — send now
    if data == "billing_trigger_now":
        await query.edit_message_text(T.BILLING_START_SENT_NOW, parse_mode="Markdown")
        context.application.create_task(
            _trigger_payment_start_reminder(context.application)
        )
        return ConversationHandler.END

    # Phase 6: skip immediate trigger
    if data == "billing_trigger_skip":
        await query.edit_message_text(T.BILLING_START_SKIPPED, parse_mode="Markdown")
        return ConversationHandler.END

    # ── Bank accounts ────────────────────────────────────────────────────────
    if data == "adm_bank":
        accounts = db.get_active_bank_accounts()
        text     = T.BANK_HEADER
        text    += "".join(
            T.BANK_ROW.format(
                bank_name=a["bank_name"],
                account_number=a["account_number"],
                account_holder=a["account_holder"],
            )
            for a in accounts
        ) if accounts else T.BANK_NONE
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=bank_keyboard(),
        )
        return ConversationHandler.END

    if data == "bank_add":
        await query.edit_message_text(T.BANK_NAME_PROMPT, parse_mode="Markdown")
        return ADM_ADD_BANK_NAME

    return ConversationHandler.END


async def receive_edit_msg_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the new message template text."""
    key   = context.user_data.get("editing_msg_key")
    label = context.user_data.get("editing_msg_label", "")
    if not key:
        return ConversationHandler.END

    new_text = update.message.text.strip()
    db.set_setting(key, new_text)
    await update.message.reply_text(
        T.EDIT_MSG_SUCCESS.format(label=label),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ─── Phase 5: receive day button callbacks ─────────────────────────────────────

async def receive_billing_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Phase 5: handle day picker button for billing start day.
    callback_data format: bill_start_day_{day}
    """
    query = update.callback_query
    await query.answer()
    data  = query.data

    if not data.startswith("bill_start_day_"):
        return ADM_BILLING_PICK_START

    try:
        day = int(data.split("_")[-1])
        assert 1 <= day <= 30
    except (ValueError, AssertionError):
        return ADM_BILLING_PICK_START

    db.set_setting("billing_start_day", str(day))
    logger.info(f"Admin {update.effective_user.id} set billing start day to {day}.")

    # Phase 6: check if today is the new start day
    now_dt         = now_eth()
    _, _, today_day = to_ethiopian(now_dt)

    if today_day == day:
        # Prompt admin: send payment-start notification now?
        await query.edit_message_text(
            T.BILLING_START_TODAY_PROMPT.format(day=day),
            parse_mode="Markdown",
            reply_markup=billing_trigger_keyboard(),
        )
        return ADM_BILLING_CONFIRM_TRIGGER
    else:
        await query.edit_message_text(
            T.BILLING_START_SAVED.format(day=day),
            parse_mode="Markdown",
        )
        return ConversationHandler.END


async def receive_billing_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Phase 5: handle day picker button for billing end day.
    callback_data format: bill_end_day_{day}
    """
    query = update.callback_query
    await query.answer()
    data  = query.data

    if not data.startswith("bill_end_day_"):
        return ADM_BILLING_PICK_END

    try:
        day = int(data.split("_")[-1])
        assert 1 <= day <= 30
    except (ValueError, AssertionError):
        return ADM_BILLING_PICK_END

    db.set_setting("billing_end_day", str(day))
    logger.info(f"Admin {update.effective_user.id} set billing end day to {day}.")

    await query.edit_message_text(
        T.BILLING_END_SAVED.format(day=day),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ─── Phase 6: background task to fire the payment start reminder immediately ──

async def _trigger_payment_start_reminder(application) -> None:
    """Fire the payment-start reminder immediately from a background task."""
    try:
        from admin.reminders import send_payment_start_reminder
        await send_payment_start_reminder(application.bot)
    except Exception as exc:
        logger.error(f"Immediate payment-start reminder failed: {exc}")


# ─── Bank account reception handlers ─────────────────────────────────────────

async def receive_bank_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_bank_name"] = update.message.text.strip()
    await update.message.reply_text(T.BANK_ACCT_PROMPT, parse_mode="Markdown")
    return ADM_ADD_BANK_ACCT


async def receive_bank_acct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_bank_acct"] = update.message.text.strip()
    await update.message.reply_text(T.BANK_HOLDER_PROMPT, parse_mode="Markdown")
    return ADM_ADD_BANK_HOLDER


async def receive_bank_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bank_name   = context.user_data.get("new_bank_name", "")
    acct_number = context.user_data.get("new_bank_acct", "")
    holder      = update.message.text.strip()

    db.add_bank_account(bank_name, acct_number, holder)
    await update.message.reply_text(
        T.BANK_ADDED.format(
            bank_name=bank_name,
            acct=acct_number,
            holder=holder,
        ),
        parse_mode="Markdown",
    )
    return ConversationHandler.END
