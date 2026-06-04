"""
admin/users.py
───────────────
User management — list all/unpaid, manual status/rename edits.

Bug fix: state integers now use unique values from admin/states.py.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from admin.states import ADM_MANUAL_USER_ID, ADM_MANUAL_ACTION, ADM_MANUAL_NEW_NAME
from keyboards.admin_keyboards import manual_action_keyboard, users_menu_keyboard
from middleware import admin_required
from texts import T

logger = logging.getLogger(__name__)

# Re-export for admin/__init__.py compatibility
MANUAL_USER_ID  = ADM_MANUAL_USER_ID
MANUAL_ACTION   = ADM_MANUAL_ACTION
MANUAL_NEW_NAME = ADM_MANUAL_NEW_NAME

_PAGE_SIZE = 30


async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user management sub-menu callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "adm_users":
        await query.edit_message_text(
            T.USERS_MENU_HEADER,
            parse_mode="Markdown",
            reply_markup=users_menu_keyboard(),
        )
        return ConversationHandler.END

    if data == "users_all":
        users = db.get_all_users()
        if not users:
            await query.edit_message_text(T.USERS_ALL_EMPTY, parse_mode="Markdown")
            return ConversationHandler.END
        lines = [T.USERS_ALL_HEADER.format(count=len(users))]
        for u in users[:_PAGE_SIZE]:
            icon = "✅" if u["status"] == "paid" else "❌"
            lines.append(f"{icon} {u['name']} — `{u['telegram_id']}`")
        if len(users) > _PAGE_SIZE:
            lines.append(T.USERS_ALL_MORE.format(n=len(users) - _PAGE_SIZE))
        await query.edit_message_text(
            "\n".join(lines), parse_mode="Markdown"
        )
        return ConversationHandler.END

    if data == "users_debtors":
        users = db.get_unpaid_users()
        if not users:
            await query.edit_message_text(T.DEBTORS_NONE, parse_mode="Markdown")
            return ConversationHandler.END
        lines = [T.DEBTORS_HEADER.format(count=len(users))]
        for u in users[:_PAGE_SIZE]:
            lines.append(f"❌ {u['name']} — `{u['telegram_id']}`")
        if len(users) > _PAGE_SIZE:
            lines.append(T.USERS_ALL_MORE.format(n=len(users) - _PAGE_SIZE))
        await query.edit_message_text(
            "\n".join(lines), parse_mode="Markdown"
        )
        return ConversationHandler.END

    if data == "users_manual":
        await query.edit_message_text(T.MANUAL_PROMPT_ID, parse_mode="Markdown")
        return ADM_MANUAL_USER_ID

    return ConversationHandler.END


async def receive_manual_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        tg_id = int(text)
    except ValueError:
        await update.message.reply_text(T.MANUAL_INVALID_ID)
        return ADM_MANUAL_USER_ID

    user = db.get_user(tg_id)
    if not user:
        await update.message.reply_text(T.MANUAL_NOT_FOUND)
        return ADM_MANUAL_USER_ID

    context.user_data["manual_target_id"] = tg_id
    icon   = "✅" if user["status"] == "paid" else "❌"
    status = user["status"]
    await update.message.reply_text(
        T.MANUAL_USER_INFO.format(
            name=user["name"], tg_id=tg_id, icon=icon, status=status
        ),
        parse_mode="Markdown",
        reply_markup=manual_action_keyboard(),
    )
    return ADM_MANUAL_ACTION


async def manual_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    data   = query.data
    tg_id  = context.user_data.get("manual_target_id")

    if not tg_id:
        return ConversationHandler.END

    if data == "manual_mark_paid":
        db.update_user_status(tg_id, "paid")
        await query.edit_message_text(
            T.MANUAL_MARKED_PAID.format(tg_id=tg_id), parse_mode="Markdown"
        )
        return ConversationHandler.END

    if data == "manual_mark_unpaid":
        db.update_user_status(tg_id, "unpaid")
        await query.edit_message_text(
            T.MANUAL_MARKED_UNPAID.format(tg_id=tg_id), parse_mode="Markdown"
        )
        return ConversationHandler.END

    if data == "manual_rename":
        await query.edit_message_text(T.MANUAL_RENAME_PROMPT, parse_mode="Markdown")
        return ADM_MANUAL_NEW_NAME

    return ConversationHandler.END


async def receive_manual_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id    = context.user_data.get("manual_target_id")
    new_name = update.message.text.strip()

    if not tg_id:
        return ConversationHandler.END

    db.update_user_name(tg_id, new_name)
    await update.message.reply_text(
        T.MANUAL_RENAME_SUCCESS.format(name=new_name), parse_mode="Markdown"
    )
    return ConversationHandler.END
