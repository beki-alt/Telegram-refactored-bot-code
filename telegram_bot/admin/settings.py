"""
admin/settings.py
──────────────────
⚙️ System settings — message templates, notifications, billing cycle, bank accounts.

FIXES / FEATURES:
 BUG-06: Cross-month billing windows (end < start) are ALLOWED. Info shown.
 BUG-07: Zero-length windows (end == start) are rejected with a popup alert.
 INLINE PICKER: Billing start/end days are now chosen via an inline keyboard
   that shows day buttons from today's Ethiopian date upward. The currently
   saved day displays a ✓ icon. Tapping a button saves immediately and
   refreshes the ✓ without leaving the picker.  A ✅ Done button exits.
   The end-day picker includes a next-month section (→1 … →5) for cross-month
   billing windows.
 EARLY NOTIFY: If the admin picks a start day equal to tomorrow, the picker
   is replaced by a Yes/No prompt to send the payment-start notification now.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

import database.client as db
from admin.states import (
    ADD_BANK_ACCT,
    ADD_BANK_HOLDER,
    ADD_BANK_NAME,
    CONFIRM_EARLY_START_NOTIFY,
    EDIT_MSG_TEXT,
    SET_BILLING_END,
    SET_BILLING_START,
)
from keyboards.admin_keyboards import (
    bank_keyboard,
    billing_cycle_keyboard,
    billing_end_day_keyboard,
    billing_start_day_keyboard,
    edit_messages_keyboard,
    notify_toggle_keyboard,
    settings_keyboard,
)
from texts import EDITABLE_MESSAGES, NOTIFICATION_KEYS, T
from utils import eth_days_in_month, eth_month_name, now_eth, to_ethiopian

logger = logging.getLogger(__name__)


# ── Shared helper ─────────────────────────────────────────────────────────────

def _billing_cycle_view(query, cycle):
    """Re-render the billing cycle overview screen."""
    return query.edit_message_text(
        T.BILLING_CYCLE_HEADER.format(start=cycle["start"], end=cycle["end"]),
        reply_markup=billing_cycle_keyboard(),
        parse_mode="Markdown",
    )


# ── Settings router ───────────────────────────────────────────────────────────

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
        await query.edit_message_text(
            T.NOTIFY_HEADER,
            reply_markup=notify_toggle_keyboard(NOTIFICATION_KEYS, db.get_setting),
            parse_mode="Markdown",
        )

    # ── Billing cycle overview ────────────────────────────────────────────────
    elif data == "adm_billing_cycle":
        cycle = db.get_billing_cycle()
        await query.edit_message_text(
            T.BILLING_CYCLE_HEADER.format(start=cycle["start"], end=cycle["end"]),
            reply_markup=billing_cycle_keyboard(),
            parse_mode="Markdown",
        )

    # ── Start day picker ──────────────────────────────────────────────────────
    elif data == "set_bill_start":
        now = now_eth()
        _, __, eth_day = to_ethiopian(now)
        cycle = db.get_billing_cycle()
        await query.edit_message_text(
            T.BILLING_START_DAY_HEADER.format(today=eth_day, current=cycle["start"]),
            reply_markup=billing_start_day_keyboard(eth_day, cycle["start"]),
            parse_mode="Markdown",
        )
        return SET_BILLING_START

    # ── End day picker ────────────────────────────────────────────────────────
    elif data == "set_bill_end":
        now = now_eth()
        _, __, eth_day = to_ethiopian(now)
        cycle      = db.get_billing_cycle()
        is_cross   = cycle["start"] > cycle["end"]
        await query.edit_message_text(
            T.BILLING_END_DAY_HEADER.format(today=eth_day, current=cycle["end"]),
            reply_markup=billing_end_day_keyboard(
                eth_day, cycle["start"], cycle["end"], is_cross
            ),
            parse_mode="Markdown",
        )
        return SET_BILLING_END

    # ── Done buttons (safety: handle stale keyboards outside conversation) ────
    elif data in ("bill_start_done", "bill_end_done"):
        cycle = db.get_billing_cycle()
        await _billing_cycle_view(query, cycle)
        return ConversationHandler.END

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


# ── Billing start day picker handler ─────────────────────────────────────────

async def handle_bill_start_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle taps on the start-day inline picker (state SET_BILLING_START).

    bill_start_done       → show billing cycle overview, end conversation.
    bill_start_pick_{day} → save day, refresh picker with ✓ on new day.
                            If day == tomorrow (Ethiopian): replace picker with
                            the early-notification Yes/No prompt and transition
                            to CONFIRM_EARLY_START_NOTIFY.
    """
    query = update.callback_query
    data  = query.data

    # ── Done ─────────────────────────────────────────────────────────────────
    if data == "bill_start_done":
        await query.answer()
        cycle = db.get_billing_cycle()
        await _billing_cycle_view(query, cycle)
        return ConversationHandler.END

    # ── Day selection ─────────────────────────────────────────────────────────
    day = int(data.split("_")[-1])   # bill_start_pick_{day}
    db.set_setting("billing_start_day", str(day))
    logger.info(f"Admin set billing_start_day → {day}.")

    now = now_eth()
    eth_year, eth_month, eth_day = to_ethiopian(now)
    days_in_month = eth_days_in_month(eth_year, eth_month)
    tomorrow_day  = eth_day + 1 if eth_day < days_in_month else 1

    # Acknowledge tap — show short toast
    await query.answer(f"✅ {day}ኛ ተቀምጧል")

    # Early notification check: if admin picked tomorrow's start day, offer
    # to send the payment-start broadcast to all users right now.
    if day == tomorrow_day:
        await query.edit_message_text(
            T.EARLY_NOTIFY_PROMPT.format(
                day        = day,
                month_name = eth_month_name(eth_month),
                today      = eth_day,
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(T.BTN_EARLY_NOTIFY_YES, callback_data="early_notify_yes"),
                InlineKeyboardButton(T.BTN_EARLY_NOTIFY_NO,  callback_data="early_notify_no"),
            ]]),
            parse_mode="Markdown",
        )
        return CONFIRM_EARLY_START_NOTIFY

    # Normal case: refresh the picker so ✓ moves to newly selected day.
    await query.edit_message_text(
        T.BILLING_START_DAY_HEADER.format(today=eth_day, current=day),
        reply_markup=billing_start_day_keyboard(eth_day, day),
        parse_mode="Markdown",
    )
    return SET_BILLING_START


# ── Early notification confirm ────────────────────────────────────────────────

async def handle_early_start_notify_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the admin's Yes / No response to the early-notification prompt.

    Yes → immediately broadcasts the payment-start reminder to all users.
    No  → simply acknowledges the day was saved; no notification is sent.
    """
    from admin.reminders import send_payment_start_reminder

    query = update.callback_query
    await query.answer()

    if query.data == "early_notify_yes":
        await send_payment_start_reminder(context)
        await query.edit_message_text(T.EARLY_NOTIFY_SENT, parse_mode="Markdown")
        logger.info("Admin triggered early payment-start notification via prompt.")
    else:
        await query.edit_message_text(T.EARLY_NOTIFY_SKIPPED, parse_mode="Markdown")
        logger.info("Admin declined early payment-start notification.")

    return ConversationHandler.END


# ── Billing end day picker handler ────────────────────────────────────────────

async def handle_bill_end_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle taps on the end-day inline picker (state SET_BILLING_END).

    bill_end_done         → show billing cycle overview, end conversation.
    bill_end_pick_{day}   → same-month day selected.
    bill_end_next_{day}   → next-month day (1-5) selected (cross-month window).

    BUG-07: If admin picks the same day as the current start day (same-month
    section only), show a popup error and stay in the picker.
    BUG-06: Picking a next-month day (→1 … →5) always produces a cross-month
    window — allowed, the header reflects it via the ✓ position.
    """
    query = update.callback_query
    data  = query.data

    # ── Done ─────────────────────────────────────────────────────────────────
    if data == "bill_end_done":
        await query.answer()
        cycle = db.get_billing_cycle()
        await _billing_cycle_view(query, cycle)
        return ConversationHandler.END

    # ── Determine selection ───────────────────────────────────────────────────
    is_next_month = data.startswith("bill_end_next_")
    day           = int(data.split("_")[-1])

    now = now_eth()
    eth_year, eth_month, eth_day = to_ethiopian(now)
    start_day = db.get_billing_cycle()["start"]

    # BUG-07: same day as start, same-month section → reject with popup
    if day == start_day and not is_next_month:
        await query.answer(T.BILLING_SAME_DAY_ALERT, show_alert=True)
        return SET_BILLING_END

    # Save the new end day
    db.set_setting("billing_end_day", str(day))
    logger.info(
        f"Admin set billing_end_day → {day} "
        f"({'next month' if is_next_month else 'same month'})."
    )

    await query.answer(f"✅ {day}ኛ ተቀምጧል")

    # Refresh picker: ✓ moves to newly selected button
    await query.edit_message_text(
        T.BILLING_END_DAY_HEADER.format(today=eth_day, current=day),
        reply_markup=billing_end_day_keyboard(
            eth_day, start_day, day, is_next_month
        ),
        parse_mode="Markdown",
    )
    return SET_BILLING_END


# ── Bank account receive ──────────────────────────────────────────────────────

async def receive_bank_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not (1 <= len(name) <= 80):
        await update.message.reply_text(T.BANK_NAME_PROMPT)
        return ADD_BANK_NAME
    context.user_data["new_bank_name"] = name
    await update.message.reply_text(T.BANK_ACCT_PROMPT)
    return ADD_BANK_ACCT


async def receive_bank_acct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acct = update.message.text.strip()
    if not (3 <= len(acct) <= 30):
        await update.message.reply_text(T.BANK_ACCT_PROMPT)
        return ADD_BANK_ACCT
    context.user_data["new_bank_acct"] = acct
    await update.message.reply_text(T.BANK_HOLDER_PROMPT)
    return ADD_BANK_HOLDER


async def receive_bank_holder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bank_name = context.user_data.get("new_bank_name", "")
    acct      = context.user_data.get("new_bank_acct", "")
    holder    = update.message.text.strip()
    if not (2 <= len(holder) <= 80):
        await update.message.reply_text(T.BANK_HOLDER_PROMPT)
        return ADD_BANK_HOLDER
    db.add_bank_account(bank_name, acct, holder)
    await update.message.reply_text(
        T.BANK_ADDED.format(bank_name=bank_name, acct=acct, holder=holder),
        parse_mode="Markdown",
    )
    logger.info(f"Admin added bank account: {bank_name} / {acct}.")
    return ConversationHandler.END
