"""
admin/inbox.py
───────────────
📩 Inbox — pending receipt approvals, support message replies, and broadcast.

FIXES:
 - BUG-05: receipt_file_id (actual photo file_id) used instead of
   receipt_channel_msg_id (a message ID, not a photo ID).
 - BUG-08: Broadcast now includes asyncio.sleep(0.05) between sends
   to stay well under Telegram's ~30 msg/s flood limit.
 - BUG-09: Support reply looks up message by ID via get_support_message_by_id()
   instead of filtering the unanswered list — so it works even if another admin
   already replied in the meantime.
 - State constants imported from states.py (globally unique integers 40-42).
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database.client as db
from admin.states import BROADCAST_TEXT, REJECT_REASON, SUPPORT_REPLY_TEXT
from keyboards.admin_keyboards import inbox_keyboard, receipt_action_keyboard, support_reply_keyboard
from texts import T
from utils import eth_storage_to_display, format_eth_date, now_eth

logger = logging.getLogger(__name__)


async def inbox_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all inbox-related inline callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    # ── Menu ──────────────────────────────────────────────────────────────────
    if data == "adm_inbox":
        await query.edit_message_text(
            T.INBOX_HEADER,
            reply_markup=inbox_keyboard(),
            parse_mode="Markdown",
        )
        return

    # ── Pending receipts ──────────────────────────────────────────────────────
    if data == "inbox_receipts":
        pending = db.get_pending_payments()
        if not pending:
            await query.edit_message_text(T.RECEIPTS_NONE, parse_mode="Markdown")
            return

        await query.edit_message_text(
            T.RECEIPTS_HEADER.format(count=len(pending)),
            parse_mode="Markdown",
        )

        for p in pending:
            user     = db.get_user(p["telegram_id"])
            name     = user["name"] if user else str(p["telegram_id"])
            # Show human-readable Ethiopian date ("28 ግንቦት 2018").
            # eth_payment_date is stored as "2018-09-28" — must convert before display.
            # Fallback to format_eth_date(now_eth()) only when field is missing entirely.
            raw_eth_date = p.get("eth_payment_date", "")
            eth_date = eth_storage_to_display(raw_eth_date) if raw_eth_date else format_eth_date(now_eth())

            caption = T.RECEIPT_REVIEW_CAPTION.format(
                name       = name,
                tg_id      = p["telegram_id"],
                eth_date   = eth_date,
                payment_id = p["id"],
            )

            # FIX: Use receipt_file_id (actual photo) not receipt_channel_msg_id (message ID)
            file_id = p.get("receipt_file_id", "")

            if file_id:
                try:
                    await query.get_bot().send_photo(
                        chat_id      = query.from_user.id,
                        photo        = file_id,
                        caption      = caption,
                        parse_mode   = "Markdown",
                        reply_markup = receipt_action_keyboard(p["id"]),
                    )
                    continue
                except Exception as exc:
                    logger.warning(f"Could not send receipt photo for payment #{p['id']}: {exc}")

            # Fallback: send text card when no file_id available (legacy records)
            await query.get_bot().send_message(
                chat_id      = query.from_user.id,
                text         = caption,
                parse_mode   = "Markdown",
                reply_markup = receipt_action_keyboard(p["id"]),
            )

    # ── Approve ───────────────────────────────────────────────────────────────
    elif data.startswith("approve_"):
        payment_id = int(data.split("_")[1])
        payment    = db.get_payment_by_id(payment_id)

        if not payment:
            await query.answer("❌ ክፍያ አልተገኘም።", show_alert=True)
            return

        db.approve_payment(payment_id)
        user = db.get_user(payment["telegram_id"])
        name = user["name"] if user else str(payment["telegram_id"])

        from utils import eth_month_name
        month_label = eth_month_name(payment["month"])
        month_year  = f"{month_label} {payment['year']}"

        approve_msg = db.get_setting("msg_approved", T.NOTIFY_APPROVED)
        try:
            msg = approve_msg.format(name=name, month=month_year)
            await query.get_bot().send_message(
                chat_id    = payment["telegram_id"],
                text       = msg,
                parse_mode = "Markdown",
            )
        except Exception as exc:
            logger.warning(f"Could not notify user {payment['telegram_id']} of approval: {exc}")

        try:
            await query.edit_message_caption(
                caption    = T.APPROVE_SUCCESS.format(payment_id=payment_id),
                parse_mode = "Markdown",
            )
        except Exception:
            await query.edit_message_text(
                T.APPROVE_SUCCESS.format(payment_id=payment_id),
                parse_mode = "Markdown",
            )
        logger.info(f"Admin approved payment #{payment_id} for user {payment['telegram_id']}.")

    # ── Reject (step 1 — ask for reason) ─────────────────────────────────────
    elif data.startswith("reject_"):
        payment_id = int(data.split("_")[1])
        context.user_data["reject_payment_id"] = payment_id
        try:
            await query.edit_message_caption(
                caption    = T.REJECT_REASON_PROMPT,
                parse_mode = "Markdown",
            )
        except Exception:
            await query.edit_message_text(
                T.REJECT_REASON_PROMPT,
                parse_mode = "Markdown",
            )
        return REJECT_REASON

    # ── Support inbox ─────────────────────────────────────────────────────────
    elif data == "inbox_support":
        msgs = db.get_unanswered_support_messages()
        if not msgs:
            await query.edit_message_text(T.SUPPORT_MSGS_NONE, parse_mode="Markdown")
            return

        await query.edit_message_text(
            T.SUPPORT_MSGS_HEADER.format(count=len(msgs)),
            parse_mode="Markdown",
        )

        for m in msgs[:10]:
            user = db.get_user(m["telegram_id"])
            name = user["name"] if user else str(m["telegram_id"])
            await query.get_bot().send_message(
                chat_id      = query.from_user.id,
                text         = T.SUPPORT_MSG_ITEM.format(
                    msg_id  = m["id"],
                    name    = name,
                    tg_id   = m["telegram_id"],
                    message = m["message"][:500],
                ),
                parse_mode   = "Markdown",
                reply_markup = support_reply_keyboard(m["id"]),
            )

    # ── Reply to support message (step 1 — ask for reply text) ───────────────
    elif data.startswith("reply_sup_"):
        msg_id  = int(data.split("_")[2])
        context.user_data["reply_support_id"] = msg_id

        # FIX: Fetch message by ID directly, not from the unanswered list
        msg_rec = db.get_support_message_by_id(msg_id)

        prompt_text = T.SUPPORT_REPLY_PROMPT.format(
            msg_id  = msg_id,
            message = msg_rec["message"] if msg_rec else "…",
        )
        await query.get_bot().send_message(
            chat_id    = query.from_user.id,
            text       = prompt_text,
            parse_mode = "Markdown",
        )
        return SUPPORT_REPLY_TEXT

    # ── Broadcast ─────────────────────────────────────────────────────────────
    elif data == "inbox_broadcast":
        await query.edit_message_text(T.BROADCAST_PROMPT, parse_mode="Markdown")
        return BROADCAST_TEXT


# ── Receive rejection reason ──────────────────────────────────────────────────

async def receive_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save rejection reason, update DB, notify user."""
    payment_id = context.user_data.get("reject_payment_id")
    reason     = update.message.text.strip()

    if not payment_id:
        await update.message.reply_text(T.EDIT_MSG_TIMEOUT)
        return ConversationHandler.END

    payment = db.get_payment_by_id(payment_id)
    if not payment:
        await update.message.reply_text("❌ ክፍያ አልተገኘም።")
        return ConversationHandler.END

    db.reject_payment(payment_id, reason)

    reject_msg = db.get_setting("msg_rejected", T.NOTIFY_REJECTED)
    try:
        msg = reject_msg.format(reason=reason)
        await update.get_bot().send_message(
            chat_id    = payment["telegram_id"],
            text       = msg,
            parse_mode = "Markdown",
        )
    except Exception as exc:
        logger.warning(f"Could not notify user {payment['telegram_id']} of rejection: {exc}")

    await update.message.reply_text(
        T.REJECT_SUCCESS.format(payment_id=payment_id), parse_mode="Markdown"
    )
    logger.info(f"Admin rejected payment #{payment_id}: {reason}")
    return ConversationHandler.END


# ── Receive support reply ─────────────────────────────────────────────────────

async def receive_support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save and send the admin's reply to a support message.
    FIX: Looks up message by ID via get_support_message_by_id() so it works
    even if the message was already answered by another admin.
    """
    msg_id     = context.user_data.get("reply_support_id")
    reply_text = update.message.text.strip()
    admin_id   = update.effective_user.id

    if not msg_id:
        await update.message.reply_text(T.EDIT_MSG_TIMEOUT)
        return ConversationHandler.END

    # FIX: look up by ID regardless of answered status
    msg_rec = db.get_support_message_by_id(msg_id)

    db.reply_to_support_message(msg_id, reply_text, admin_id)

    if msg_rec:
        try:
            await update.get_bot().send_message(
                chat_id    = msg_rec["telegram_id"],
                text       = T.SUPPORT_REPLY_TO_USER.format(reply=reply_text),
                parse_mode = "Markdown",
            )
        except Exception as exc:
            logger.warning(f"Could not send reply to user {msg_rec['telegram_id']}: {exc}")
    else:
        logger.warning(f"Support message #{msg_id} not found in DB — reply saved but user not notified.")

    await update.message.reply_text(T.SUPPORT_REPLY_SUCCESS)
    logger.info(f"Admin {admin_id} replied to support message #{msg_id}.")
    return ConversationHandler.END


# ── Receive broadcast ─────────────────────────────────────────────────────────

async def receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a text or photo broadcast to all registered users.
    FIX: asyncio.sleep(0.05) added between sends to avoid Telegram flood control.
    """
    users = db.get_all_users()

    await update.message.reply_text(T.BROADCAST_SENDING.format(count=len(users)))

    sent   = 0
    failed = 0

    for user in users:
        try:
            if update.message.photo:
                await update.get_bot().send_photo(
                    chat_id    = user["telegram_id"],
                    photo      = update.message.photo[-1].file_id,
                    caption    = update.message.caption or "",
                    parse_mode = "Markdown",
                )
            else:
                await update.get_bot().send_message(
                    chat_id    = user["telegram_id"],
                    text       = update.message.text or "",
                    parse_mode = "Markdown",
                )
            sent += 1
        except Exception as exc:
            logger.warning(f"Broadcast failed for user {user['telegram_id']}: {exc}")
            failed += 1

        # FIX: rate limiting — Telegram allows ~30 messages/second
        await asyncio.sleep(0.05)

    await update.message.reply_text(
        T.BROADCAST_DONE.format(sent=sent, failed=failed), parse_mode="Markdown"
    )
    logger.info(f"Broadcast complete — sent: {sent}, failed: {failed}.")
    return ConversationHandler.END
