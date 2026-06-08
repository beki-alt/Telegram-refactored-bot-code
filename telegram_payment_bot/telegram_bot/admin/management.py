"""
admin/management.py
────────────────────
🛡️ Admin management — add, remove, and list admin users.
Only the super admin may add or remove other admins.

FIX: State constant ADD_ADMIN_ID imported from states.py (globally unique = 10).
"""

import logging

from telegram import BotCommand, BotCommandScopeChat, Update
from telegram.ext import ContextTypes, ConversationHandler

import database.client as db
from admin.states import ADD_ADMIN_ID
from keyboards.admin_keyboards import admin_manage_keyboard, remove_admin_keyboard
from texts import T

logger = logging.getLogger(__name__)


async def admin_manage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin management inline button callbacks."""
    query   = update.callback_query
    await query.answer()
    data    = query.data
    user_id = query.from_user.id

    if data == "adm_manage":
        await query.edit_message_text(
            T.MANAGE_HEADER,
            reply_markup=admin_manage_keyboard(),
            parse_mode="Markdown",
        )
        return

    # All actions below require super-admin
    if not db.is_super_admin(user_id):
        await query.answer(T.MANAGE_SUPER_ONLY, show_alert=True)
        return

    if data == "adm_add_admin":
        await query.edit_message_text(T.ADD_ADMIN_PROMPT, parse_mode="Markdown")
        return ADD_ADMIN_ID

    elif data == "adm_remove_admin":
        admins = db.get_all_admins()
        if not admins:
            await query.edit_message_text(T.REMOVE_ADMIN_NONE)
            return ConversationHandler.END
        await query.edit_message_text(
            T.REMOVE_ADMIN_HEADER,
            reply_markup=remove_admin_keyboard(admins),
            parse_mode="Markdown",
        )

    elif data == "adm_list_admins":
        admins = db.get_all_admins()
        if not admins:
            text = T.LIST_ADMINS_EMPTY
        else:
            lines = [T.LIST_ADMINS_HEADER]
            for i, a in enumerate(admins, 1):
                role = T.ADMIN_ROLE_SUPER if a.get("is_super") else T.ADMIN_ROLE_REGULAR
                lines.append(f"{i}. ID: `{a['telegram_id']}` — {role}")
            text = "\n".join(lines)
        from keyboards.admin_keyboards import back_button
        await query.edit_message_text(text, reply_markup=back_button("adm_manage"), parse_mode="Markdown")

    elif data.startswith("remove_adm_"):
        tid = int(data.split("_")[2])
        if db.remove_admin(tid):
            # Remove /admin from the ex-admin's command menu
            try:
                await query.get_bot().set_my_commands(
                    _PUBLIC_COMMANDS,
                    scope=BotCommandScopeChat(chat_id=tid),
                )
            except Exception as exc:
                logger.warning(f"Could not clear admin commands for {tid}: {exc}")
            await query.edit_message_text(
                T.REMOVE_ADMIN_SUCCESS.format(tg_id=tid), parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(T.REMOVE_ADMIN_SUPER_ERROR)


_ADMIN_COMMANDS = [
    BotCommand("start",  "ቦቱን ጀምር"),
    BotCommand("cancel", "ሂደቱን ሰርዝ"),
    BotCommand("admin",  "የአስተዳዳሪ ፓነል"),
]
_PUBLIC_COMMANDS = [
    BotCommand("start",  "ቦቱን ጀምር"),
    BotCommand("cancel", "ሂደቱን ሰርዝ"),
]


async def receive_add_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and save the new admin's Telegram ID."""
    try:
        new_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(T.ADD_ADMIN_INVALID)
        return ADD_ADMIN_ID

    db.add_admin(new_id, update.effective_user.id, is_super=False)

    # Show /admin in the new admin's command menu immediately
    try:
        await update.get_bot().set_my_commands(
            _ADMIN_COMMANDS,
            scope=BotCommandScopeChat(chat_id=new_id),
        )
    except Exception as exc:
        logger.warning(f"Could not set admin commands for {new_id}: {exc}")

    await update.message.reply_text(T.ADD_ADMIN_SUCCESS.format(tg_id=new_id), parse_mode="Markdown")
    logger.info(f"Admin {update.effective_user.id} added new admin {new_id}.")
    return ConversationHandler.END
