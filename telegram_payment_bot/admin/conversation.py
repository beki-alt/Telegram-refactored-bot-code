"""
admin/conversation.py
──────────────────────
Builds and returns the master admin ConversationHandler.

All admin conversation states and entry points are wired here
so main.py stays clean and only needs to call build_admin_conversation().
"""

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from admin.inbox import (
    BROADCAST_TEXT,
    REJECT_REASON,
    SUPPORT_REPLY_TEXT,
    inbox_callback,
    receive_broadcast,
    receive_reject_reason,
    receive_support_reply,
)
from admin.management import ADD_ADMIN_ID, admin_manage_callback, receive_add_admin_id
from admin.panel import admin_panel, admin_panel_callback, cancel_conv
from admin.reports import report_callback
from admin.settings import (
    ADD_BANK_ACCT,
    ADD_BANK_HOLDER,
    ADD_BANK_NAME,
    EDIT_MSG_TEXT,
    SET_BILLING_END,
    SET_BILLING_START,
    receive_bank_acct,
    receive_bank_holder,
    receive_bank_name,
    receive_billing_end,
    receive_billing_start,
    receive_edit_msg_text,
    settings_callback,
)
from admin.users import (
    MANUAL_ACTION,
    MANUAL_NEW_NAME,
    MANUAL_USER_ID,
    manual_action_callback,
    receive_manual_new_name,
    receive_manual_user_id,
    users_callback,
)


def build_admin_conversation() -> ConversationHandler:
    """Assemble and return the master admin ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_panel),
            CallbackQueryHandler(
                admin_manage_callback,
                pattern=r"^adm_(add_admin|remove_admin|list_admins)$|^remove_adm_",
            ),
            CallbackQueryHandler(
                settings_callback,
                pattern=r"^adm_(edit_msgs|notify_toggle|billing_cycle|bank|settings)"
                        r"|^edit_msg_|^toggle_|^set_bill_|^bank_",
            ),
            CallbackQueryHandler(users_callback,  pattern=r"^users_|^adm_users$"),
            CallbackQueryHandler(
                inbox_callback,
                pattern=r"^inbox_|^approve_|^reject_|^reply_sup_|^adm_inbox$",
            ),
            CallbackQueryHandler(report_callback, pattern=r"^report_|^adm_report$"),
            CallbackQueryHandler(
                admin_panel_callback,
                pattern=r"^adm_(manage|settings|users|inbox|report|back)$",
            ),
        ],
        states={
            ADD_ADMIN_ID:    [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_admin_id)],
            EDIT_MSG_TEXT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_msg_text)],
            SET_BILLING_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_billing_start)],
            SET_BILLING_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_billing_end)],
            ADD_BANK_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_name)],
            ADD_BANK_ACCT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_acct)],
            ADD_BANK_HOLDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_holder)],
            MANUAL_USER_ID:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_user_id)],
            MANUAL_ACTION:   [CallbackQueryHandler(manual_action_callback, pattern=r"^manual_")],
            MANUAL_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_new_name)],
            REJECT_REASON:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reject_reason)],
            SUPPORT_REPLY_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_reply)],
            BROADCAST_TEXT:  [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast),
                MessageHandler(filters.PHOTO, receive_broadcast),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        allow_reentry=True,
        per_message=False,
    )
