"""
admin/inbox.py
───────────────
Admin inbox — pending receipts, support messages, broadcast.

Bug fixes from original:
  1. Receipt display used send_photo(photo=msg_id) — message IDs are NOT file IDs.
     Fix: use receipt_file_id (stored Telegram file_id) or forward from channel.
     The TelegramStorageService handles the fallback chain gracefully.
  2. query.answer() was called twice in reply_sup_ handler. Removed duplicate.
  3. State integers now use unique values from admin/states.py.
"""

import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from admin.states import ADM_REJECT_REASON, ADM_SUPPORT_REPLY, ADM_BROADCAST_TEXT
from keyboards.admin_keyboards import (
    inbox_keyboard,
    receipt_action_keyboard,
    support_reply_keyboard,
)
from storage import storage as tg_storage
from texts import T
from utils import eth_month_name

logger = logging.getLogger(__name__)

# Re-export for admin/__init__.py compatibility
REJECT_REASON     = ADM_REJECT_REASON
SUPPORT_REPLY_TEXT = ADM_SUPPORT_REPLY
BROADCAST_TEXT     = ADM_BROADCAST_TEXT


async def inbox_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inbox sub-menu callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    # ── Main inbox menu ──────────────────────────────────────────────────────
    if data == "adm_inbox":
        await query.edit_message_text(
            T.INBOX_HEADER,
            parse_mode="Markdown",
            reply_markup=inbox_keyboard(),
        )
        return ConversationHandler.END

    # ── Pending receipts ─────────────────────────────────────────────────────
    if data == "inbox_receipts":
        pending = db.get_pending_payments()
        if not pending:
            await query.edit_message_text(T.RECEIPTS_NONE, parse_mode="Markdown")
            return ConversationHandler.END

        await query.edit_message_text(
            T.RECEIPTS_HEADER.format(count=len(pending)), parse_mode="Markdown"
        )

        bot = query.get_bot()
        for p in pending:
            user        = db.get_user(p["telegram_id"])
            user_name   = user["name"] if user else str(p["telegram_id"])
            payment_id  = p["id"]
            eth_date    = p.get("eth_payment_date", "")

            # Build caption
            caption = T.RECEIPT_REVIEW_CAPTION.format(
                name       = user_name,
                tg_id      = p["telegram_id"],
                eth_date   = eth_date,
                payment_id = payment_id,
            )

            # FIX: use stored receipt_file_id; fall back to channel forward
            file_id        = p.get("receipt_file_id") or None
            channel_msg_id = p.get("receipt_channel_msg_id") or None

            await tg_storage.send_photo_to_admin(
                bot          = bot,
                admin_chat_id= query.message.chat_id,
                file_id      = file_id,
                channel_msg_id = channel_msg_id,
                caption      = caption,
                reply_markup = receipt_action_keyboard(payment_id),
            )
        return ConversationHandler.END

    # ── Approve a payment ────────────────────────────────────────────────────
    if data.startswith("approve_"):
        try:
            payment_id = int(data.split("_", 1)[1])
        except (IndexError, ValueError):
            return ConversationHandler.END

        payment = db.get_payment_by_id(payment_id)
        if not payment:
            await query.edit_message_text("❌ ክፍያ አልተገኘም።")
            return ConversationHandler.END

        approved = db.approve_payment(payment_id)
        if approved:
            user = db.get_user(payment["telegram_id"])
            month_name = eth_month_name(payment.get("month", 0))
            year       = payment.get("year", "")
            await query.edit_message_text(
                T.APPROVE_SUCCESS.format(payment_id=payment_id),
                parse_mode="Markdown",
            )
            # Notify user
            if user:
                try:
                    await query.get_bot().send_message(
                        chat_id    = payment["telegram_id"],
                        text       = T.NOTIFY_APPROVED.format(
                            name  = user["name"],
                            month = f"{month_name} {year}",
                        ),
                        parse_mode = "Markdown",
                    )
                except Exception:
                    logger.warning(
                        f"Could not notify user {payment['telegram_id']} of approval."
                    )
        else:
            await query.edit_message_text("❌ ክፍያ ማጽደቅ አልተሳካም።")
        return ConversationHandler.END

    # ── Begin reject flow ────────────────────────────────────────────────────
    if data.startswith("reject_"):
        try:
            payment_id = int(data.split("_", 1)[1])
        except (IndexError, ValueError):
            return ConversationHandler.END

        context.user_data["rejecting_payment_id"] = payment_id
        await query.edit_message_text(T.REJECT_REASON_PROMPT, parse_mode="Markdown")
        return ADM_REJECT_REASON

    # ── Support inbox ────────────────────────────────────────────────────────
    if data == "inbox_support":
        msgs = db.get_unanswered_support_messages()
        if not msgs:
            await query.edit_message_text(T.SUPPORT_MSGS_NONE, parse_mode="Markdown")
            return ConversationHandler.END

        text = T.SUPPORT_MSGS_HEADER.format(count=len(msgs))
        for m in msgs[:10]:
            text += T.SUPPORT_MSG_ITEM.format(
                msg_id  = m["id"],
                name    = db.get_user(m["telegram_id"]).get("name", str(m["telegram_id"]))
                          if db.get_user(m["telegram_id"]) else str(m["telegram_id"]),
                tg_id   = m["telegram_id"],
                message = m["message"],
            )
        await query.edit_message_text(text, parse_mode="Markdown")

        # Send reply-button for each message
        bot = query.get_bot()
        for m in msgs[:10]:
            await bot.send_message(
                chat_id      = query.message.chat_id,
                text         = f"#{m['id']}",
                reply_markup = support_reply_keyboard(m["id"]),
            )
        return ConversationHandler.END

    # ── Begin support reply flow ─────────────────────────────────────────────
    if data.startswith("reply_sup_"):
        try:
            msg_id = int(data.split("_")[-1])
        except (IndexError, ValueError):
            return ConversationHandler.END

        support_msg = db.get_support_message_by_id(msg_id)
        if not support_msg:
            await query.edit_message_text("❌ ጥያቄ አልተገኘም።")
            return ConversationHandler.END

        context.user_data["replying_support_msg_id"] = msg_id
        # FIX: removed duplicate query.answer() — already called at top
        await query.edit_message_text(
            T.SUPPORT_REPLY_PROMPT.format(
                msg_id  = msg_id,
                message = support_msg["message"],
            ),
            parse_mode="Markdown",
        )
        return ADM_SUPPORT_REPLY

    # ── Broadcast ────────────────────────────────────────────────────────────
    if data == "inbox_broadcast":
        await query.edit_message_text(T.BROADCAST_PROMPT, parse_mode="Markdown")
        return ADM_BROADCAST_TEXT

    return ConversationHandler.END


async def receive_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save rejection reason and notify the user."""
    payment_id = context.user_data.get("rejecting_payment_id")
    if not payment_id:
        return ConversationHandler.END

    reason  = update.message.text.strip()
    payment = db.get_payment_by_id(payment_id)

    db.reject_payment(payment_id, reason)
    await update.message.reply_text(
        T.REJECT_SUCCESS.format(payment_id=payment_id), parse_mode="Markdown"
    )

    # Notify user
    if payment:
        try:
            await update.get_bot().send_message(
                chat_id    = payment["telegram_id"],
                text       = T.NOTIFY_REJECTED.format(reason=reason),
                parse_mode = "Markdown",
            )
        except Exception:
            logger.warning(
                f"Could not notify user {payment.get('telegram_id')} of rejection."
            )
    return ConversationHandler.END


async def receive_support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save and send the admin's reply to a support message."""
    msg_id   = context.user_data.get("replying_support_msg_id")
    admin_id = update.effective_user.id
    if not msg_id:
        return ConversationHandler.END

    reply_text  = update.message.text.strip()
    support_msg = db.get_support_message_by_id(msg_id)

    if not support_msg:
        await update.message.reply_text("❌ ጥያቄ አልተገኘም።")
        return ConversationHandler.END

    db.reply_to_support_message(msg_id, reply_text, admin_id)
    await update.message.reply_text(T.SUPPORT_REPLY_SUCCESS, parse_mode="Markdown")

    # Notify user
    target_tg_id = support_msg.get("telegram_id")
    if target_tg_id:
        try:
            await update.get_bot().send_message(
                chat_id    = target_tg_id,
                text       = T.SUPPORT_REPLY_TO_USER.format(reply=reply_text),
                parse_mode = "Markdown",
            )
        except Exception:
            logger.warning(
                f"Could not deliver support reply to user {target_tg_id}."
            )
    return ConversationHandler.END


async def receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast a message to all registered users."""
    users = db.get_all_users()
    bot   = update.get_bot()
    sent = failed = 0

    await update.message.reply_text(
        T.BROADCAST_SENDING.format(count=len(users)), parse_mode="Markdown"
    )

    for user in users:
        try:
            if update.message.photo:
                await bot.send_photo(
                    chat_id   = user["telegram_id"],
                    photo     = update.message.photo[-1].file_id,
                    caption   = update.message.caption or "",
                )
            elif update.message.document:
                await bot.send_document(
                    chat_id  = user["telegram_id"],
                    document = update.message.document.file_id,
                    caption  = update.message.caption or "",
                )
            else:
                await bot.send_message(
                    chat_id    = user["telegram_id"],
                    text       = update.message.text or "",
                    parse_mode = "Markdown",
                )
            sent += 1
        except Exception as exc:
            logger.warning(f"Broadcast failed for {user['telegram_id']}: {exc}")
            failed += 1

    await update.message.reply_text(
        T.BROADCAST_DONE.format(sent=sent, failed=failed), parse_mode="Markdown"
    )
    return ConversationHandler.END
