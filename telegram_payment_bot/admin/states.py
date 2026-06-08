"""
admin/states.py
────────────────
SINGLE SOURCE OF TRUTH for all admin ConversationHandler state integers.

CRITICAL: Every constant here must be globally unique across ALL admin
modules so the master ConversationHandler in conversation.py never
has colliding state keys in its states={} dictionary.

Ranges:
  10–19  Management
  20–29  Settings
  30–39  Users
  40–49  Inbox
"""

# ── Admin management ──────────────────────────────────────────────────────────
ADD_ADMIN_ID = 10

# ── Settings ──────────────────────────────────────────────────────────────────
EDIT_MSG_TEXT    = 20
SET_BILLING_START = 21
SET_BILLING_END   = 22
ADD_BANK_NAME    = 23
ADD_BANK_ACCT    = 24
ADD_BANK_HOLDER  = 25
CONFIRM_EARLY_START_NOTIFY = 26   # admin prompt: send notification now?

# ── User management ───────────────────────────────────────────────────────────
MANUAL_USER_ID  = 30
MANUAL_ACTION   = 31
MANUAL_NEW_NAME = 32

# ── Inbox ──────────────────────────────────────────────────────────────────────
REJECT_REASON      = 40
SUPPORT_REPLY_TEXT = 41
BROADCAST_TEXT     = 42
