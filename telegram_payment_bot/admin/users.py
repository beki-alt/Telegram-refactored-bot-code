"""
admin/users.py
───────────────
👥 User management — list users, view debtors, manually edit user status and name.

FIX: State constants imported from states.py (globally unique integers 30-32).
FIX: escape_markdown applied to u['name'] to prevent Telegram BadRequest crash.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.helpers import escape_markdown

import database.client as db
from admin.states import MANUAL_ACTION, MANUAL_NEW_NAME, MANUAL_USER_ID
from keyboards.admin_keyboards import back_button, manual_action_keyboard, users_menu_keyboard
from texts import T

logger = logging.getLogger(__name__)


async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all user-management inline callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "adm_users":
        await query.edit_message_text(
            T.USERS_MENU_HEADER,
            reply_markup=users_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    if data == "users_all":
        users = db.get_all_users()
        if not users:
            await query.edit_message_text(T.USERS_ALL_EMPTY)
            return
        lines = [T.USERS_ALL_HEADER.format(count=len(users))]
        for u in users[:50]:
            icon = "✅" if u["status"] == "paid" else "❌"
            safe_name = escape_markdown(u["name"], version=1)
            lines.append(f"{icon} {safe_name} — `{u['telegram_id']}`")
        if len(users) > 50:
            lines.append(T.USERS_ALL_MORE.format(n=len(users) - 50))
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=back_button("adm_users"),
            parse_mode="Markdown",
        )

    elif data == "users_debtors":
        debtors = db.get_unpaid_users()
        if not debtors:
            await query.edit_message_text(T.DEBTORS_NONE)
            return
        lines = [T.DEBTORS_HEADER.format(count=len(debtors))]
        for u in debtors[:50]:
            lines.append(f"• {u['name']} — `{u['telegram_id']}`")
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=back_button("adm_users"),
            parse_mode="Markdown",
        )

    elif data == "users_manual":
        await query.edit_message_text(T.MANUAL_PROMPT_ID, parse_mode="Markdown")
        return MANUAL_USER_ID


async def receive_manual_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive target user ID for manual editing."""
    try:
        uid = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(T.MANUAL_INVALID_ID)
        return MANUAL_USER_ID

    user = db.get_user(uid)
    if not user:
        await update.message.reply_text(T.MANUAL_NOT_FOUND)
        return MANUAL_USER_ID

    context.user_data["manual_target_id"] = uid
    icon = "✅" if user["status"] == "paid" else "❌"

    await update.message.reply_text(
        T.MANUAL_USER_INFO.format(
            name   = user["name"],
            tg_id  = uid,
            icon   = icon,
            status = user["status"],
        ),
        reply_markup=manual_action_keyboard(),
        parse_mode="Markdown",
    )
    return MANUAL_ACTION


async def manual_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mark-paid / mark-unpaid / rename actions for a user."""
    query = update.callback_query
    await query.answer()
    data  = query.data
    uid   = context.user_data.get("manual_target_id")

    if data == "manual_mark_paid":
        db.update_user_status(uid, "paid")
        await query.edit_message_text(T.MANUAL_MARKED_PAID.format(tg_id=uid), parse_mode="Markdown")
        logger.info(f"Admin manually marked user {uid} as paid.")
        return ConversationHandler.END

    elif data == "manual_mark_unpaid":
        db.update_user_status(uid, "unpaid")
        await query.edit_message_text(T.MANUAL_MARKED_UNPAID.format(tg_id=uid), parse_mode="Markdown")
        logger.info(f"Admin manually marked user {uid} as unpaid.")
        return ConversationHandler.END

    elif data == "manual_rename":
        await query.edit_message_text(T.MANUAL_RENAME_PROMPT)
        return MANUAL_NEW_NAME


async def receive_manual_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the admin-assigned new name for a user."""
    uid      = context.user_data.get("manual_target_id")
    new_name = update.message.text.strip()

    if len(new_name) < 2 or len(new_name) > 60:
        await update.message.reply_text(T.EDIT_NAME_TOO_SHORT)
        return MANUAL_NEW_NAME

    db.update_user_name(uid, new_name)
    await update.message.reply_text(
        T.MANUAL_RENAME_SUCCESS.format(name=new_name), parse_mode="Markdown"
    )
    logger.info(f"Admin renamed user {uid} to '{new_name}'.")
    return ConversationHandler.END
