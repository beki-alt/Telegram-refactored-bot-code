"""
admin/settings.py
──────────────────
⚙️ System settings — message templates, notifications, billing cycle, bank accounts.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from keyboards.admin_keyboards import (
    bank_keyboard,
    billing_cycle_keyboard,
    edit_messages_keyboard,
    notify_toggle_keyboard,
    settings_keyboard,
)
from texts import EDITABLE_MESSAGES, NOTIFICATION_KEYS, T

logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────────────────
EDIT_MSG_TEXT   = 0
SET_BILLING_START = 1
SET_BILLING_END   = 2
ADD_BANK_NAME   = 3
ADD_BANK_ACCT   = 4
ADD_BANK_HOLDER = 5


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all settings-related inline callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    # ── Edit message templates ────────────────────────────────────────────────
    if data == "adm_edit_msgs":
        await query.edit_message_text(
            T.EDIT_MSG_HEADER,
            reply_markup=edit_messages_keyboard(EDITABLE_MESSAGES),
            parse_mode="Markdown",
        )

    elif data.startswith("edit_msg_"):
        key     = data[len("edit_msg_"):]
        label   = EDITABLE_MESSAGES.get(key, key)
        current = db.get_setting(key, "")
        context.user_data["edit_msg_key"] = key
        await query.edit_message_text(
            T.EDIT_MSG_PROMPT.format(label=label, current=current),
            parse_mode="Markdown",
        )
        return EDIT_MSG_TEXT

    # ── Notification toggles ──────────────────────────────────────────────────
    elif data == "adm_notify_toggle":
        await query.edit_message_text(
            T.NOTIFY_HEADER,
            reply_markup=notify_toggle_keyboard(NOTIFICATION_KEYS, db.get_setting),
            parse_mode="Markdown",
        )

    elif data.startswith("toggle_"):
        key     = data[len("toggle_"):]
        current = db.get_setting(key, "true")
        new_val = "false" if current == "true" else "true"
        db.set_setting(key, new_val)
        status  = T.NOTIFY_ON if new_val == "true" else T.NOTIFY_OFF
        label   = NOTIFICATION_KEYS.get(key, key)
        await query.answer(f"{label}: {status}", show_alert=True)
        # Refresh toggle menu
        await query.edit_message_text(
            T.NOTIFY_HEADER,
            reply_markup=notify_toggle_keyboard(NOTIFICATION_KEYS, db.get_setting),
            parse_mode="Markdown",
        )

    # ── Billing cycle ─────────────────────────────────────────────────────────
    elif data == "adm_billing_cycle":
        cycle = db.get_billing_cycle()
        await query.edit_message_text(
            T.BILLING_CYCLE_HEADER.format(start=cycle["start"], end=cycle["end"]),
            reply_markup=billing_cycle_keyboard(),
            parse_mode="Markdown",
        )

    elif data == "set_bill_start":
        await query.edit_message_text(T.BILLING_START_PROMPT)
        return SET_BILLING_START

    elif data == "set_bill_end":
        await query.edit_message_text(T.BILLING_END_PROMPT)
        return SET_BILLING_END

    # ── Bank accounts ─────────────────────────────────────────────────────────
    elif data == "adm_bank":
        accounts = db.get_active_bank_accounts()
        text = T.BANK_HEADER
        if accounts:
            for a in accounts:
                text += T.BANK_ROW.format(
                    bank_name      = a["bank_name"],
                    account_number = a["account_number"],
                    account_holder = a["account_holder"],
                )
        else:
            text += T.BANK_NONE
        await query.edit_message_text(text, reply_markup=bank_keyboard(), parse_mode="Markdown")

    elif data == "bank_add":
        await query.edit_message_text(T.BANK_NAME_PROMPT)
        return ADD_BANK_NAME

    # ── Back to settings ──────────────────────────────────────────────────────
    elif data == "adm_settings":
        await query.edit_message_text(
            T.SETTINGS_HEADER,
            reply_markup=settings_keyboard(),
            parse_mode="Markdown",
        )


# ── Message edit receive ──────────────────────────────────────────────────────

async def receive_edit_msg_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("edit_msg_key")
    if not key:
        await update.message.reply_text(T.EDIT_MSG_TIMEOUT)
        return ConversationHandler.END
    label = EDITABLE_MESSAGES.get(key, key)
    db.set_setting(key, update.message.text)
    await update.message.reply_text(T.EDIT_MSG_SUCCESS.format(label=label), parse_mode="Markdown")
    logger.info(f"Admin updated message template '{key}'.")
    return ConversationHandler.END


# ── Billing cycle receive ─────────────────────────────────────────────────────

async def receive_billing_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        day = int(update.message.text.strip())
        assert 1 <= day <= 30
    except (ValueError, AssertionError):
        await update.message.reply_text(T.BILLING_INVALID)
        return SET_BILLING_START
    db.set_setting("billing_start_day", str(day))
    await update.message.reply_text(T.BILLING_START_SAVED.format(day=day), parse_mode="Markdown")
    return ConversationHandler.END


async def receive_billing_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        day = int(update.message.text.strip())
        assert 1 <= day <= 30
    except (ValueError, AssertionError):
        await update.message.reply_text(T.BILLING_INVALID)
        return SET_BILLING_END
    db.set_setting("billing_end_day", str(day))
    await update.message.reply_text(T.BILLING_END_SAVED.format(day=day), parse_mode="Markdown")
    return ConversationHandler.END


# ── Bank account receive ──────────────────────────────────────────────────────

async def receive_bank_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_bank_name"] = update.message.text.strip()
    await update.message.reply_text(T.BANK_ACCT_PROMPT)
    return ADD_BANK_ACCT


async def receive_bank_acct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_bank_acct"] = update.message.text.strip()
    await update.message.reply_text(T.BANK_HOLDER_PROMPT)
    return ADD_BANK_HOLDER


async def receive_bank_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bank_name = context.user_data.get("new_bank_name", "")
    acct      = context.user_data.get("new_bank_acct", "")
    holder    = update.message.text.strip()
    db.add_bank_account(bank_name, acct, holder)
    await update.message.reply_text(
        T.BANK_ADDED.format(bank_name=bank_name, acct=acct, holder=holder),
        parse_mode="Markdown",
    )
    logger.info(f"Admin added bank account: {bank_name} / {acct}.")
    return ConversationHandler.END
