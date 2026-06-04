"""
admin/management.py
────────────────────
Admin management — add/remove/list admins.

Bug fix: original used ADD_ADMIN_ID=0 which conflicted with all other state-0
constants. Now uses ADM_ADD_ADMIN_ID=10 from admin/states.py.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from admin.states import ADM_ADD_ADMIN_ID
from keyboards.admin_keyboards import (
    admin_main_menu_keyboard,
    admin_manage_keyboard,
    remove_admin_keyboard,
)
from middleware import super_admin_required
from texts import T

logger = logging.getLogger(__name__)

# Re-export the constant for admin/__init__.py compatibility
ADD_ADMIN_ID = ADM_ADD_ADMIN_ID


@super_admin_required
async def admin_manage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin management sub-menu callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "adm_manage":
        await query.edit_message_text(
            T.MANAGE_HEADER,
            parse_mode="Markdown",
            reply_markup=admin_manage_keyboard(),
        )
        return ConversationHandler.END

    if data == "adm_add_admin":
        await query.edit_message_text(T.ADD_ADMIN_PROMPT, parse_mode="Markdown")
        return ADM_ADD_ADMIN_ID

    if data == "adm_remove_admin":
        admins = db.get_all_admins()
        non_super = [a for a in admins if not a.get("is_super")]
        if not non_super:
            await query.edit_message_text(T.REMOVE_ADMIN_NONE, parse_mode="Markdown")
            return ConversationHandler.END
        await query.edit_message_text(
            T.REMOVE_ADMIN_HEADER,
            parse_mode="Markdown",
            reply_markup=remove_admin_keyboard(admins),
        )
        return ConversationHandler.END

    if data == "adm_list_admins":
        admins = db.get_all_admins()
        if not admins:
            await query.edit_message_text(T.LIST_ADMINS_EMPTY, parse_mode="Markdown")
            return ConversationHandler.END
        lines = [T.LIST_ADMINS_HEADER]
        for a in admins:
            role  = T.ADMIN_ROLE_SUPER if a.get("is_super") else T.ADMIN_ROLE_REGULAR
            lines.append(f"{role} `{a['telegram_id']}`")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    if data.startswith("remove_adm_"):
        try:
            tg_id = int(data.split("_")[2])
        except (IndexError, ValueError):
            return ConversationHandler.END
        removed = db.remove_admin(tg_id)
        if removed:
            await query.edit_message_text(
                T.REMOVE_ADMIN_SUCCESS.format(tg_id=tg_id), parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                T.REMOVE_ADMIN_SUPER_ERROR, parse_mode="Markdown"
            )
        return ConversationHandler.END

    return ConversationHandler.END


async def receive_add_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the Telegram ID for the new admin."""
    text = update.message.text.strip()
    try:
        new_tg_id = int(text)
    except ValueError:
        await update.message.reply_text(T.ADD_ADMIN_INVALID)
        return ADM_ADD_ADMIN_ID

    db.add_admin(new_tg_id, added_by=update.effective_user.id, is_super=False)
    await update.message.reply_text(
        T.ADD_ADMIN_SUCCESS.format(tg_id=new_tg_id),
        parse_mode="Markdown",
    )
    logger.info(f"Admin {update.effective_user.id} added new admin {new_tg_id}.")
    return ConversationHandler.END
