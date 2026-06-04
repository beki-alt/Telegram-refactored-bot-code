"""
admin/conversation.py
──────────────────────
Builds and returns the master admin ConversationHandler.

FIXES:
 - BUG-04: All state integers are now imported from admin/states.py which
   guarantees global uniqueness (10-49 range).  Previously every module
   used 0,1,2 which caused Python dict key collisions — only the last
   assignment for each integer survived, breaking 9 out of 12 admin flows.
 - Entry-point patterns tightened: adm_settings/users/inbox/report are now
   caught exclusively by their specialized callbacks, not by admin_panel_callback
   (which only handles adm_manage, adm_back, and the /admin command response).
"""

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from admin.inbox import (
    inbox_callback,
    receive_broadcast,
    receive_reject_reason,
    receive_support_reply,
)
from admin.management import admin_manage_callback, receive_add_admin_id
from admin.panel import admin_panel, admin_panel_callback, cancel_conv
from admin.reports import report_callback
from admin.settings import (
    receive_bank_acct,
    receive_bank_holder,
    receive_bank_name,
    receive_billing_end,
    receive_billing_start,
    receive_edit_msg_text,
    settings_callback,
)
from admin.states import (
    ADD_ADMIN_ID,
    ADD_BANK_ACCT,
    ADD_BANK_HOLDER,
    ADD_BANK_NAME,
    BROADCAST_TEXT,
    EDIT_MSG_TEXT,
    MANUAL_ACTION,
    MANUAL_NEW_NAME,
    MANUAL_USER_ID,
    REJECT_REASON,
    SET_BILLING_END,
    SET_BILLING_START,
    SUPPORT_REPLY_TEXT,
)
from admin.users import (
    manual_action_callback,
    receive_manual_new_name,
    receive_manual_user_id,
    users_callback,
)


def build_admin_conversation() -> ConversationHandler:
    """
    Assemble and return the master admin ConversationHandler.

    State integers (all unique, from admin/states.py):
      10 — ADD_ADMIN_ID
      20 — EDIT_MSG_TEXT
      21 — SET_BILLING_START
      22 — SET_BILLING_END
      23 — ADD_BANK_NAME
      24 — ADD_BANK_ACCT
      25 — ADD_BANK_HOLDER
      30 — MANUAL_USER_ID
      31 — MANUAL_ACTION
      32 — MANUAL_NEW_NAME
      40 — REJECT_REASON
      41 — SUPPORT_REPLY_TEXT
      42 — BROADCAST_TEXT
    """
    return ConversationHandler(
        entry_points=[
            # /admin command
            CommandHandler("admin", admin_panel),

            # Admin management (add/remove/list admins)
            CallbackQueryHandler(
                admin_manage_callback,
                pattern=r"^adm_(add_admin|remove_admin|list_admins|manage)$|^remove_adm_",
            ),

            # Settings (messages, notifications, billing, bank)
            CallbackQueryHandler(
                settings_callback,
                pattern=(
                    r"^adm_(edit_msgs|notify_toggle|billing_cycle|bank|settings)$"
                    r"|^edit_msg_|^toggle_|^set_bill_|^bank_"
                ),
            ),

            # User management
            CallbackQueryHandler(
                users_callback,
                pattern=r"^users_|^adm_users$",
            ),

            # Inbox (receipts, approvals, rejections, support, broadcast)
            CallbackQueryHandler(
                inbox_callback,
                pattern=r"^inbox_|^approve_|^reject_|^reply_sup_|^adm_inbox$",
            ),

            # Reports
            CallbackQueryHandler(
                report_callback,
                pattern=r"^report_|^adm_report$",
            ),

            # Top-level navigation (back button + adm_manage panel view)
            CallbackQueryHandler(
                admin_panel_callback,
                pattern=r"^adm_(back)$",
            ),
        ],
        states={
            # ── Management ────────────────────────────────────────────────────
            ADD_ADMIN_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_admin_id)
            ],

            # ── Settings ──────────────────────────────────────────────────────
            EDIT_MSG_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_msg_text)
            ],
            SET_BILLING_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_billing_start)
            ],
            SET_BILLING_END: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_billing_end)
            ],
            ADD_BANK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_name)
            ],
            ADD_BANK_ACCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_acct)
            ],
            ADD_BANK_HOLDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_holder)
            ],

            # ── User management ───────────────────────────────────────────────
            MANUAL_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_user_id)
            ],
            MANUAL_ACTION: [
                CallbackQueryHandler(manual_action_callback, pattern=r"^manual_")
            ],
            MANUAL_NEW_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_new_name)
            ],

            # ── Inbox ──────────────────────────────────────────────────────────
            REJECT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reject_reason)
            ],
            SUPPORT_REPLY_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_reply)
            ],
            BROADCAST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast),
                MessageHandler(filters.PHOTO, receive_broadcast),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        allow_reentry=True,
        per_message=False,
        name="admin_conversation",
        persistent=False,
    )
