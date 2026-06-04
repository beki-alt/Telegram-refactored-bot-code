"""
admin/conversation.py
──────────────────────
Assembles the single admin ConversationHandler from all sub-module handlers.

BUG FIX — Critical: the original code had duplicate state integer keys.
All sub-modules used state 0 for their first state. In a Python dict, duplicate
keys overwrite earlier entries. This means states from management.py, settings.py,
and inbox.py were silently discarded — only users.py state 0 survived.

Fix: all state constants are now unique integers defined in admin/states.py.
  management: 10
  settings:   20, 30, 31, 32, 40, 41, 42
  users:      50, 51, 52
  inbox:      60, 61, 62

The assembled states dict has NO duplicate keys.
"""

import logging

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from admin.panel      import admin_panel_callback, cancel_conv
from admin.management import admin_manage_callback, receive_add_admin_id
from admin.settings   import (
    settings_callback,
    receive_edit_msg_text,
    receive_billing_start,
    receive_billing_end,
    receive_bank_name,
    receive_bank_acct,
    receive_bank_holder,
)
from admin.users      import (
    users_callback,
    receive_manual_user_id,
    manual_action_callback,
    receive_manual_new_name,
)
from admin.inbox      import (
    inbox_callback,
    receive_reject_reason,
    receive_support_reply,
    receive_broadcast,
)
from admin.reports    import report_callback
from admin.states     import (
    ADM_ADD_ADMIN_ID,
    ADM_EDIT_MSG_TEXT,
    ADM_BILLING_PICK_START,
    ADM_BILLING_PICK_END,
    ADM_BILLING_CONFIRM_TRIGGER,
    ADM_ADD_BANK_NAME,
    ADM_ADD_BANK_ACCT,
    ADM_ADD_BANK_HOLDER,
    ADM_MANUAL_USER_ID,
    ADM_MANUAL_ACTION,
    ADM_MANUAL_NEW_NAME,
    ADM_REJECT_REASON,
    ADM_SUPPORT_REPLY,
    ADM_BROADCAST_TEXT,
)

logger = logging.getLogger(__name__)


def build_admin_conversation() -> ConversationHandler:
    """
    Build and return the admin ConversationHandler.

    All entry points are CallbackQueryHandlers so the admin panel is
    accessed via /admin → inline buttons only.

    State integers are unique (no overlaps) — see admin/states.py.
    """
    # Entry points: handle all top-level admin panel callbacks
    entry_points = [
        # Panel navigation
        CallbackQueryHandler(admin_panel_callback, pattern=r"^adm_back$"),
        # Section entries
        CallbackQueryHandler(admin_manage_callback,  pattern=r"^adm_manage$"),
        CallbackQueryHandler(settings_callback,      pattern=r"^adm_settings$"),
        CallbackQueryHandler(users_callback,         pattern=r"^adm_users$"),
        CallbackQueryHandler(inbox_callback,         pattern=r"^adm_inbox$"),
        CallbackQueryHandler(report_callback,        pattern=r"^adm_report$"),
    ]

    states = {
        # ── Management ────────────────────────────────────────────────────────
        ADM_ADD_ADMIN_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_admin_id),
        ],

        # ── Settings ──────────────────────────────────────────────────────────
        ADM_EDIT_MSG_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_msg_text),
        ],

        # Phase 5: billing cycle day pickers (callback-based, no text input)
        ADM_BILLING_PICK_START: [
            CallbackQueryHandler(receive_billing_start, pattern=r"^bill_start_day_\d+$"),
            CallbackQueryHandler(settings_callback,     pattern=r"^adm_billing_cycle$"),
        ],
        ADM_BILLING_PICK_END: [
            CallbackQueryHandler(receive_billing_end, pattern=r"^bill_end_day_\d+$"),
            CallbackQueryHandler(settings_callback,   pattern=r"^adm_billing_cycle$"),
        ],

        # Phase 6: immediate trigger confirmation
        ADM_BILLING_CONFIRM_TRIGGER: [
            CallbackQueryHandler(
                settings_callback,
                pattern=r"^(billing_trigger_now|billing_trigger_skip)$",
            ),
        ],

        ADM_ADD_BANK_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_name),
        ],
        ADM_ADD_BANK_ACCT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_acct),
        ],
        ADM_ADD_BANK_HOLDER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bank_holder),
        ],

        # ── Users ─────────────────────────────────────────────────────────────
        ADM_MANUAL_USER_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_user_id),
        ],
        ADM_MANUAL_ACTION: [
            CallbackQueryHandler(
                manual_action_callback,
                pattern=r"^manual_(mark_paid|mark_unpaid|rename)$",
            ),
        ],
        ADM_MANUAL_NEW_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_new_name),
        ],

        # ── Inbox ─────────────────────────────────────────────────────────────
        ADM_REJECT_REASON: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reject_reason),
        ],
        ADM_SUPPORT_REPLY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_reply),
        ],
        ADM_BROADCAST_TEXT: [
            MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
                receive_broadcast,
            ),
        ],

        # ── Wildcard states: all inline callbacks that don't start a new flow ──
        # These are catch-all handlers that process navigation and sub-menus
        # without moving to a specific state.
        ConversationHandler.END: [
            # Navigation callbacks
            CallbackQueryHandler(admin_panel_callback,  pattern=r"^adm_back$"),
            CallbackQueryHandler(admin_manage_callback, pattern=r"^(adm_manage|adm_add_admin|adm_remove_admin|adm_list_admins|remove_adm_\d+)$"),
            CallbackQueryHandler(settings_callback,     pattern=r"^(adm_settings|adm_edit_msgs|edit_msg_\w+|adm_notify_toggle|toggle_\w+|adm_billing_cycle|set_bill_start|set_bill_end|adm_bank|bank_add|billing_trigger_now|billing_trigger_skip)$"),
            CallbackQueryHandler(users_callback,        pattern=r"^(adm_users|users_all|users_debtors|users_manual)$"),
            CallbackQueryHandler(inbox_callback,        pattern=r"^(adm_inbox|inbox_receipts|inbox_support|inbox_broadcast|approve_\d+|reject_\d+|reply_sup_\d+)$"),
            CallbackQueryHandler(report_callback,       pattern=r"^(adm_report|report_quick|report_excel_pick|report_attend_pick|report_notify_pick|report_excel_\d+_\d+|report_attend_\d+_\d+|report_nfy_\d+_\d+|report_nfyok_\d+_\d+)$"),
        ],
    }

    fallbacks = [CommandHandler("cancel", cancel_conv)]

    return ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=fallbacks,
        allow_reentry=True,
        per_chat=True,
        per_user=True,
        per_message=False,
    )
