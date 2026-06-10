"""
admin/conversation.py
──────────────────────
Builds and returns the master admin ConversationHandler.

FIXES:
 - BUG-04: All state integers are now imported from admin/states.py which
   guarantees global uniqueness (10-49 range).
 - INLINE PICKER: SET_BILLING_START and SET_BILLING_END states now use
   CallbackQueryHandler (day-picker buttons) instead of MessageHandler
   (manual text input).  The ✓ indicator moves to the selected day on each
   tap; a ✅ Done button exits back to the billing cycle overview.
 - NEW FEATURE: CONFIRM_EARLY_START_NOTIFY state (26) wires the Yes/No
   inline buttons shown when the admin picks tomorrow as the new start day.
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
    handle_bill_end_pick,
    handle_bill_start_pick,
    handle_early_start_notify_confirm,
    receive_bank_acct,
    receive_bank_holder,
    receive_bank_name,
    receive_edit_msg_text,
    settings_callback,
)
from admin.states import (
    ADD_ADMIN_ID,
    ADD_BANK_ACCT,
    ADD_BANK_HOLDER,
    ADD_BANK_NAME,
    BROADCAST_TEXT,
    CONFIRM_EARLY_START_NOTIFY,
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
      21 — SET_BILLING_START   ← inline day-picker (bill_start_pick_* / bill_start_done)
      22 — SET_BILLING_END     ← inline day-picker (bill_end_pick_* / bill_end_next_* / bill_end_done)
      23 — ADD_BANK_NAME
      24 — ADD_BANK_ACCT
      25 — ADD_BANK_HOLDER
      26 — CONFIRM_EARLY_START_NOTIFY
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
            # Also includes bill_start_done / bill_end_done so stale keyboards
            # work even if the conversation has already ended.
            CallbackQueryHandler(
                settings_callback,
                pattern=(
                    r"^adm_(edit_msgs|notify_toggle|billing_cycle|bank|settings)$"
                    r"|^edit_msg_|^toggle_|^set_bill_|^bank_"
                    r"|^bill_(start|end)_done$"
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

            # Top-level navigation (back button)
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

            # Inline day-picker for billing start day.
            # bill_start_pick_{d} → save & refresh ✓; bill_start_done → exit.
            SET_BILLING_START: [
                CallbackQueryHandler(
                    handle_bill_start_pick,
                    pattern=r"^bill_start_(pick_\d+|done)$",
                )
            ],

            # Yes/No prompt when admin picks tomorrow as the new start day.
            CONFIRM_EARLY_START_NOTIFY: [
                CallbackQueryHandler(
                    handle_early_start_notify_confirm,
                    pattern=r"^early_notify_(yes|no)$",
                )
            ],

            # Inline day-picker for billing end day.
            # bill_end_pick_{d}  → same-month day; bill_end_next_{d} → next-month day.
            # bill_end_done      → exit.
            SET_BILLING_END: [
                CallbackQueryHandler(
                    handle_bill_end_pick,
                    pattern=r"^bill_end_(pick_\d+|next_\d+|done)$",
                )
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
