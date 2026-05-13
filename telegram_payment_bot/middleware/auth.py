"""
middleware/auth.py
──────────────────
Decorator-based authorization guards for admin and super-admin handlers.

Usage:
    @admin_required
    async def my_handler(update, context): ...

    @super_admin_required
    async def super_handler(update, context): ...
"""

import logging
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from texts import T

logger = logging.getLogger(__name__)


def admin_required(func):
    """
    Decorator: allow only users who are admins (regular or super).
    Ends any active conversation for unauthorized callers.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not db.is_admin(user_id):
            msg = update.effective_message
            if msg:
                await msg.reply_text(T.ADMIN_NOT_AUTHORIZED)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


def super_admin_required(func):
    """
    Decorator: allow only the super admin.
    Ends any active conversation for unauthorized callers.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not db.is_super_admin(user_id):
            msg = update.effective_message
            if msg:
                await msg.reply_text(T.ADMIN_SUPER_ONLY)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper
