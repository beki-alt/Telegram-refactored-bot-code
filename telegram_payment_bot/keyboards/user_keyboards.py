"""
keyboards/user_keyboards.py
────────────────────────────
Reply and inline keyboards for regular users.
All labels come from texts.T.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from texts import T


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [T.BTN_MY_PROFILE, T.BTN_PAY_RENEW],
            [T.BTN_SCHEDULE,   T.BTN_SUPPORT],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(T.BTN_SHARE_PHONE, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_EDIT_NAME,  callback_data="profile_edit_name")],
        [InlineKeyboardButton(T.BTN_EDIT_PHONE, callback_data="profile_edit_phone")],
    ])


def payment_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(T.BTN_CONFIRM_PAYMENT, callback_data="confirm_payment"),
            InlineKeyboardButton(T.BTN_CANCEL_PAYMENT,  callback_data="cancel_payment"),
        ]
    ])


def support_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_PAYMENT_HISTORY, callback_data="history_view")],
        [InlineKeyboardButton(T.BTN_CONTACT_SUPPORT, callback_data="support_contact")],
    ])
