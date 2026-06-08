"""
database/__init__.py
─────────────────────
Re-exports all public database functions from client.py so that
the rest of the codebase can do:

    import database as db
    db.get_user(tg_id)
"""

from .client import (
    # Bootstrap
    init_tables,
    ping_supabase,

    # Users
    register_user,
    complete_user_registration,
    get_user,
    get_all_users,
    get_unpaid_users,
    get_paid_users,
    update_user_name,
    update_user_phone,
    update_user_status,
    get_total_users_count,
    reset_all_users_to_unpaid,

    # Admins
    add_admin,
    remove_admin,
    get_all_admins,
    is_admin,
    is_super_admin,

    # Payments
    create_payment_record,
    get_pending_payments,
    get_payment_by_id,
    approve_payment,
    reject_payment,
    get_user_payment_history,
    has_pending_or_approved_payment,
    get_monthly_payments,
    get_total_paid_this_month,
    get_unpaid_users_for_month,
    get_attendance_data,
    get_cycle_summary,

    # Settings
    get_setting,
    set_setting,
    get_all_settings,
    get_billing_cycle,

    # Bank accounts
    get_active_bank_accounts,
    add_bank_account,
    deactivate_bank_account,

    # Support messages
    create_support_message,
    get_unanswered_support_messages,
    get_support_message_by_id,
    reply_to_support_message,
)

__all__ = [
    "init_tables", "ping_supabase",
    "register_user", "complete_user_registration",
    "get_user", "get_all_users", "get_unpaid_users",
    "get_paid_users", "update_user_name", "update_user_phone",
    "update_user_status", "get_total_users_count", "reset_all_users_to_unpaid",
    "add_admin", "remove_admin", "get_all_admins", "is_admin", "is_super_admin",
    "create_payment_record", "get_pending_payments", "get_payment_by_id",
    "approve_payment", "reject_payment", "get_user_payment_history",
    "has_pending_or_approved_payment",
    "get_monthly_payments", "get_total_paid_this_month",
    "get_unpaid_users_for_month", "get_attendance_data", "get_cycle_summary",
    "get_setting", "set_setting", "get_all_settings", "get_billing_cycle",
    "get_active_bank_accounts", "add_bank_account", "deactivate_bank_account",
    "create_support_message", "get_unanswered_support_messages",
    "get_support_message_by_id", "reply_to_support_message",
]
