"""
handlers/support.py
────────────────────
📝 Support & History — payment history view and support message submission.
"""

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database.client as db
from keyboards.user_keyboards import main_menu_keyboard, support_menu_keyboard
from texts import T
from utils import eth_month_name

logger = logging.getLogger(__name__)

SUPPORT_MSG_INPUT = 0


async def support_and_history(update: Update, context) -> None:
    """Show the support & history menu."""
    await update.message.reply_text(
        T.SUPPORT_MENU_HEADER,
        parse_mode="Markdown",
        reply_markup=support_menu_keyboard(),
    )


async def support_history_callback(update: Update, context):
    """Handle callbacks from the support menu."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "history_view":
        tg_id   = query.from_user.id
        history = db.get_user_payment_history(tg_id)

        if not history:
            await query.edit_message_text(T.HISTORY_EMPTY, parse_mode="Markdown")
            return ConversationHandler.END

        lines = [T.HISTORY_HEADER]
        for p in history[:10]:
            if p["status"] == "approved":
                icon       = T.HISTORY_APPROVED
                status_str = T.HISTORY_STATUS_APPROVED
            elif p["status"] == "rejected":
                icon       = T.HISTORY_REJECTED
                status_str = T.HISTORY_STATUS_REJECTED
            else:
                icon       = T.HISTORY_PENDING
                status_str = T.HISTORY_STATUS_PENDING

            # Prefer stored Ethiopian date; fall back to month/year fields
            eth_date = p.get("eth_payment_date", "")
            if eth_date:
                parts = eth_date.split("-")
                if len(parts) == 3:
                    try:
                        date_display = f"{eth_month_name(int(parts[1]))} {parts[0]} (ዓ.ም)"
                    except (ValueError, IndexError):
                        date_display = eth_date
                else:
                    date_display = eth_date
            else:
                # Safely fallback — both keys must exist to avoid KeyError
                m = p.get("month")
                y = p.get("year")
                date_display = f"{eth_month_name(m)} {y} (ዓ.ም)" if m and y else "—"

            lines.append(f"{icon} {date_display} — {status_str}")

        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
        return ConversationHandler.END

    if data == "support_contact":
        await query.edit_message_text(T.SUPPORT_PROMPT, parse_mode="Markdown")
        return SUPPORT_MSG_INPUT


async def receive_support_message(update: Update, context):
    """Save the user's support message and acknowledge receipt."""
    tg_id = update.effective_user.id
    msg   = (update.message.text or "").strip()

    if len(msg) < 5:
        await update.message.reply_text(T.SUPPORT_TOO_SHORT)
        return SUPPORT_MSG_INPUT

    db.create_support_message(tg_id, msg)
    logger.info(f"Support message from user {tg_id}.")

    await update.message.reply_text(
        T.SUPPORT_SENT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def cancel_support(update: Update, context) -> int:
    await update.message.reply_text(
        T.OPERATION_CANCELLED,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


def build_support_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                support_history_callback,
                pattern=r"^(history_view|support_contact)$",
            ),
        ],
        states={
            SUPPORT_MSG_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_message)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_support)],
        allow_reentry=True,
        name="support",
        persistent=False,
    )
