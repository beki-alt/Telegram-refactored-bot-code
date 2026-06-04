"""
admin/states.py
────────────────
SINGLE SOURCE OF TRUTH for all admin ConversationHandler states.

BUG FIX: The original code defined state constants starting at 0 in each
sub-module (management.py, settings.py, inbox.py, users.py). When assembled
into one ConversationHandler, duplicate integer keys were silently overwritten
by Python's dict, leaving only the last definition active for each integer.

Fix: unique integers across ALL admin sub-modules.
"""

# ── Admin management ───────────────────────────────────────────────────────────
ADM_ADD_ADMIN_ID     = 10

# ── Settings — message templates ──────────────────────────────────────────────
ADM_EDIT_MSG_TEXT    = 20

# ── Settings — billing cycle (Phase 5: button-based) ─────────────────────────
ADM_BILLING_PICK_START = 30   # waiting for admin to pick start day button
ADM_BILLING_PICK_END   = 31   # waiting for admin to pick end day button
ADM_BILLING_CONFIRM_TRIGGER = 32  # Phase 6: prompt "send now?" after start-day save

# ── Settings — bank accounts ──────────────────────────────────────────────────
ADM_ADD_BANK_NAME    = 40
ADM_ADD_BANK_ACCT    = 41
ADM_ADD_BANK_HOLDER  = 42

# ── User management ───────────────────────────────────────────────────────────
ADM_MANUAL_USER_ID   = 50
ADM_MANUAL_ACTION    = 51
ADM_MANUAL_NEW_NAME  = 52

# ── Inbox — receipt rejection ─────────────────────────────────────────────────
ADM_REJECT_REASON    = 60

# ── Inbox — support replies ───────────────────────────────────────────────────
ADM_SUPPORT_REPLY    = 61

# ── Inbox — broadcast ────────────────────────────────────────────────────────
ADM_BROADCAST_TEXT   = 62
