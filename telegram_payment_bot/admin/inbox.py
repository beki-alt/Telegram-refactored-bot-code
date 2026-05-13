"""
admin/inbox.py
───────────────
📩 Inbox — pending receipt approvals, support message replies, and broadcast.
"""

import logging
import traceback

from telegram import InputFile, Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from keyboards.admin_keyboards import inbox_keyboard, receipt_action_keyboard, support_reply_keyboard
from texts import T
from utils import format_eth_date, now_eth

logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────────────────
REJECT_REASON    = 0
SUPPORT_REPLY_TEXT = 1
BROADCAST_TEXT   = 2


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
            user = db.get_user(p["telegram_id"])
            name = user["name"] if user else str(p["telegram_id"])
            eth_date = p.get("eth_payment_date", format_eth_date(now_eth()))

            caption = T.RECEIPT_REVIEW_CAPTION.format(
                name       = name,
                tg_id      = p["telegram_id"],
                eth_date   = eth_date,
                payment_id = p["id"],
            )

            try:
                await query.get_bot().send_photo(
                    chat_id     = query.from_user.id,
                    photo       = p.get("receipt_channel_msg_id", ""),
                    caption     = caption,
                    parse_mode  = "Markdown",
                    reply_markup = receipt_action_keyboard(p["id"]),
                )
            except Exception:
                # If direct photo-by-ID fails, send text-only approval card
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

        # Notify the user
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

        await query.edit_message_caption(
            caption    = T.APPROVE_SUCCESS.format(payment_id=payment_id),
            parse_mode = "Markdown",
        )
        logger.info(f"Admin approved payment #{payment_id} for user {payment['telegram_id']}.")

    # ── Reject (step 1 — ask for reason) ─────────────────────────────────────
    elif data.startswith("reject_"):
        payment_id = int(data.split("_")[1])
        context.user_data["reject_payment_id"] = payment_id
        await query.edit_message_caption(
            caption    = T.REJECT_REASON_PROMPT,
            parse_mode = "Markdown",
        )
        return REJECT_REASON

    # ── Support inbox ─────────────────────────────────────────────────────────
    elif data == "inbox_support":
        msgs = db.get_unanswered_support_messages()
        if not msgs:
            await query.edit_message_text(T.SUPPORT_MSGS_NONE, parse_mode="Markdown")
            return

        text = T.SUPPORT_MSGS_HEADER.format(count=len(msgs))
        for m in msgs[:10]:
            user = db.get_user(m["telegram_id"])
            name = user["name"] if user else str(m["telegram_id"])
            text += T.SUPPORT_MSG_ITEM.format(
                msg_id  = m["id"],
                name    = name,
                tg_id   = m["telegram_id"],
                message = m["message"][:200],
            )

        rows = [support_reply_keyboard(m["id"]) for m in msgs[:10]]
        # Send as multiple messages — one per support ticket
        await query.edit_message_text(text, parse_mode="Markdown")
        for m in msgs[:10]:
            user = db.get_user(m["telegram_id"])
            name = user["name"] if user else str(m["telegram_id"])
            await query.get_bot().send_message(
                chat_id      = query.from_user.id,
                text         = T.SUPPORT_MSG_ITEM.format(
                    msg_id  = m["id"],
                    name    = name,
                    tg_id   = m["telegram_id"],
                    message = m["message"],
                ),
                parse_mode   = "Markdown",
                reply_markup = support_reply_keyboard(m["id"]),
            )

    # ── Reply to support message (step 1 — ask for reply text) ───────────────
    elif data.startswith("reply_sup_"):
        msg_id = int(data.split("_")[2])
        context.user_data["reply_support_id"] = msg_id
        msg_rec = None
        msgs = db.get_unanswered_support_messages()
        for m in msgs:
            if m["id"] == msg_id:
                msg_rec = m
                break

        prompt_text = T.SUPPORT_REPLY_PROMPT.format(
            msg_id  = msg_id,
            message = msg_rec["message"] if msg_rec else "…",
        )
        await query.answer()
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

    # Notify the user
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
    """Save and send the admin's reply to a support message."""
    msg_id     = context.user_data.get("reply_support_id")
    reply_text = update.message.text.strip()
    admin_id   = update.effective_user.id

    if not msg_id:
        await update.message.reply_text(T.EDIT_MSG_TIMEOUT)
        return ConversationHandler.END

    # Find the original support message to get the user's TG ID
    msgs = db.get_unanswered_support_messages()
    target = next((m for m in msgs if m["id"] == msg_id), None)

    db.reply_to_support_message(msg_id, reply_text, admin_id)

    if target:
        try:
            await update.get_bot().send_message(
                chat_id    = target["telegram_id"],
                text       = T.SUPPORT_REPLY_TO_USER.format(reply=reply_text),
                parse_mode = "Markdown",
            )
        except Exception as exc:
            logger.warning(f"Could not send reply to user {target['telegram_id']}: {exc}")

    await update.message.reply_text(T.SUPPORT_REPLY_SUCCESS)
    logger.info(f"Admin {admin_id} replied to support message #{msg_id}.")
    return ConversationHandler.END


# ── Receive broadcast ─────────────────────────────────────────────────────────

async def receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a text or photo broadcast to all registered users."""
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

    await update.message.reply_text(
        T.BROADCAST_DONE.format(sent=sent, failed=failed), parse_mode="Markdown"
    )
    logger.info(f"Broadcast complete — sent: {sent}, failed: {failed}.")
    return ConversationHandler.END
