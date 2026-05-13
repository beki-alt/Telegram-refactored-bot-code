"""
keyboards/admin_keyboards.py
─────────────────────────────
Inline keyboards used throughout the admin panel.
All button labels come from texts.T.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from texts import T
from utils import prev_eth_months, eth_month_name


def admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_ADM_MANAGE,   callback_data="adm_manage")],
        [InlineKeyboardButton(T.BTN_ADM_SETTINGS, callback_data="adm_settings")],
        [InlineKeyboardButton(T.BTN_ADM_USERS,    callback_data="adm_users")],
        [InlineKeyboardButton(T.BTN_ADM_INBOX,    callback_data="adm_inbox")],
        [InlineKeyboardButton(T.BTN_ADM_REPORT,   callback_data="adm_report")],
    ])


def back_button(callback: str = "adm_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_BACK, callback_data=callback)]])


# ── Admin management ──────────────────────────────────────────────────────────

def admin_manage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_ADD_ADMIN,    callback_data="adm_add_admin")],
        [InlineKeyboardButton(T.BTN_REMOVE_ADMIN, callback_data="adm_remove_admin")],
        [InlineKeyboardButton(T.BTN_LIST_ADMINS,  callback_data="adm_list_admins")],
        [InlineKeyboardButton(T.BTN_BACK,         callback_data="adm_back")],
    ])


def remove_admin_keyboard(admins: list) -> InlineKeyboardMarkup:
    rows = []
    for a in admins:
        if not a.get("is_super"):
            rows.append([InlineKeyboardButton(
                f"🗑 ID: {a['telegram_id']}",
                callback_data=f"remove_adm_{a['telegram_id']}",
            )])
    rows.append([InlineKeyboardButton(T.BTN_BACK, callback_data="adm_manage")])
    return InlineKeyboardMarkup(rows)


# ── Settings ──────────────────────────────────────────────────────────────────

def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_EDIT_MESSAGES, callback_data="adm_edit_msgs")],
        [InlineKeyboardButton(T.BTN_NOTIFY_TOGGLE, callback_data="adm_notify_toggle")],
        [InlineKeyboardButton(T.BTN_BILLING_CYCLE, callback_data="adm_billing_cycle")],
        [InlineKeyboardButton(T.BTN_BANK_ACCOUNTS,  callback_data="adm_bank")],
        [InlineKeyboardButton(T.BTN_BACK,           callback_data="adm_back")],
    ])


def edit_messages_keyboard(editable: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"edit_msg_{key}")]
        for key, label in editable.items()
    ]
    rows.append([InlineKeyboardButton(T.BTN_BACK, callback_data="adm_settings")])
    return InlineKeyboardMarkup(rows)


def notify_toggle_keyboard(notification_keys: dict, get_setting_fn) -> InlineKeyboardMarkup:
    rows = []
    for key, label in notification_keys.items():
        current = get_setting_fn(key, "true")
        status  = T.NOTIFY_ON if current == "true" else T.NOTIFY_OFF
        rows.append([InlineKeyboardButton(f"{label} — {status}", callback_data=f"toggle_{key}")])
    rows.append([InlineKeyboardButton(T.BTN_BACK, callback_data="adm_settings")])
    return InlineKeyboardMarkup(rows)


def billing_cycle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_EDIT_START_DAY, callback_data="set_bill_start")],
        [InlineKeyboardButton(T.BTN_EDIT_END_DAY,   callback_data="set_bill_end")],
        [InlineKeyboardButton(T.BTN_BACK,           callback_data="adm_settings")],
    ])


def bank_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_ADD_BANK, callback_data="bank_add")],
        [InlineKeyboardButton(T.BTN_BACK,     callback_data="adm_settings")],
    ])


# ── User management ───────────────────────────────────────────────────────────

def users_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_ALL_USERS,   callback_data="users_all")],
        [InlineKeyboardButton(T.BTN_DEBTORS,     callback_data="users_debtors")],
        [InlineKeyboardButton(T.BTN_MANUAL_EDIT, callback_data="users_manual")],
        [InlineKeyboardButton(T.BTN_BACK,        callback_data="adm_back")],
    ])


def manual_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_MARK_PAID,   callback_data="manual_mark_paid")],
        [InlineKeyboardButton(T.BTN_MARK_UNPAID, callback_data="manual_mark_unpaid")],
        [InlineKeyboardButton(T.BTN_RENAME_USER, callback_data="manual_rename")],
    ])


# ── Inbox ──────────────────────────────────────────────────────────────────────

def inbox_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_PENDING_RECEIPTS, callback_data="inbox_receipts")],
        [InlineKeyboardButton(T.BTN_SUPPORT_INBOX,    callback_data="inbox_support")],
        [InlineKeyboardButton(T.BTN_BROADCAST,        callback_data="inbox_broadcast")],
        [InlineKeyboardButton(T.BTN_BACK,             callback_data="adm_back")],
    ])


def receipt_action_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(T.BTN_APPROVE, callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton(T.BTN_REJECT,  callback_data=f"reject_{payment_id}"),
        ]
    ])


def support_reply_keyboard(msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💬 #{msg_id} ምላሽ ስጥ", callback_data=f"reply_sup_{msg_id}")]
    ])


# ── Reports ───────────────────────────────────────────────────────────────────

def report_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_QUICK_REPORT,  callback_data="report_quick")],
        [InlineKeyboardButton(T.BTN_PAYMENT_EXCEL, callback_data="report_excel_pick")],
        [InlineKeyboardButton(T.BTN_ATTEND_EXCEL,  callback_data="report_attend_pick")],
        [InlineKeyboardButton(T.BTN_NOTIFY_UNPAID, callback_data="report_notify_pick")],
        [InlineKeyboardButton(T.BTN_BACK,          callback_data="adm_back")],
    ])


def month_picker_keyboard(prefix: str, n: int = 6) -> InlineKeyboardMarkup:
    """Build a month picker: last n Ethiopian months, 2 per row."""
    months = prev_eth_months(n)
    rows = []
    for i in range(0, len(months), 2):
        row = []
        for y, m in months[i:i + 2]:
            label = f"{eth_month_name(m)} {y}"
            row.append(InlineKeyboardButton(label, callback_data=f"{prefix}_{y}_{m}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(T.BTN_BACK, callback_data="adm_report")])
    return InlineKeyboardMarkup(rows)
