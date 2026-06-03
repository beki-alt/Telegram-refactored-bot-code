"""
keyboards/user_keyboards.py
────────────────────────────
Reply and inline keyboards shown to regular users.
All button labels come from texts.T so they are centralized.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from texts import T

from telegram import KeyboardButton, ReplyKeyboardMarkup

def contact_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 ስልክ ቁጥር አጋራ",
                    request_contact=True
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent bottom keyboard shown on the main menu."""
    return ReplyKeyboardMarkup(
        [
            [T.BTN_MY_PROFILE,  T.BTN_PAY_RENEW],
            [T.BTN_SCHEDULE,    T.BTN_SUPPORT],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    """Inline buttons shown below the profile card."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_EDIT_NAME, callback_data="profile_edit_name")],
    ])


def payment_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm / cancel buttons after the user uploads a receipt screenshot."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(T.BTN_CONFIRM_PAYMENT, callback_data="confirm_payment"),
            InlineKeyboardButton(T.BTN_CANCEL_PAYMENT,  callback_data="cancel_payment"),
        ]
    ])


def support_menu_keyboard() -> InlineKeyboardMarkup:
    """Support & history menu inline buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_PAYMENT_HISTORY, callback_data="history_view")],
        [InlineKeyboardButton(T.BTN_CONTACT_SUPPORT, callback_data="support_contact")],
    ])
