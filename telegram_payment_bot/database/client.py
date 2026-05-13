"""
database/client.py
───────────────────
Supabase data access layer.

All database operations are here. No SQL or Supabase calls
should exist anywhere else in the codebase.

Table overview:
  users           — registered Telegram users + payment status
  admins          — admin users (regular + super)
  payments        — payment submission records + approval status
  settings        — key/value config store (billing cycle, messages, toggles)
  bank_accounts   — payment destination accounts shown to users
  support_messages — user support requests + admin replies
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

import config

logger = logging.getLogger(__name__)

# ── Supabase singleton ────────────────────────────────────────────────────────
_supabase: Optional[Client] = None


def _db() -> Client:
    """Return (and lazily create) the Supabase client singleton."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabase


# ── Schema bootstrap ──────────────────────────────────────────────────────────

def init_tables() -> None:
    """
    Seed default settings on first boot.
    The actual table DDL should be applied once in the Supabase SQL editor
    (see SQL at the bottom of this file for reference).
    """
    _seed_default_settings()
    logger.info("Database: default settings seeded.")


def _seed_default_settings() -> None:
    """Insert default settings only if they do not already exist."""
    from texts import T

    defaults: Dict[str, str] = {
        "billing_start_day":   "25",
        "billing_end_day":     "5",
        "msg_payment_start":   T.DEFAULT_MSG_PAYMENT_START,
        "msg_reminder_one_day": T.DEFAULT_MSG_ONE_DAY,
        "msg_final_day":       T.DEFAULT_MSG_FINAL_DAY,
        "msg_approved":        T.NOTIFY_APPROVED,
        "msg_rejected":        T.NOTIFY_REJECTED,
        "notify_payment_start": "true",
        "notify_one_day":      "true",
        "notify_final_day":    "true",
    }
    sb = _db()
    for key, value in defaults.items():
        try:
            sb.table("settings").upsert(
                {"key": key, "value": value},
                on_conflict="key",
                ignore_duplicates=True,
            ).execute()
        except Exception as exc:
            logger.warning(f"Settings seed warning [{key}]: {exc}")


# ── Keep-alive ────────────────────────────────────────────────────────────────

async def ping_supabase() -> None:
    """Ping Supabase every 48 h to prevent free-tier connection sleep."""
    while True:
        try:
            _db().table("settings").select("key").limit(1).execute()
            logger.info("Supabase keep-alive ping OK.")
        except Exception as exc:
            logger.error(f"Supabase ping failed: {exc}")
        await asyncio.sleep(48 * 3600)


# ── User operations ───────────────────────────────────────────────────────────

def register_user(telegram_id: int, name: str) -> Dict[str, Any]:
    """
    Register a new user or return the existing record.
    Safe to call on every /start — idempotent.
    """
    sb = _db()
    existing = sb.table("users").select("*").eq("telegram_id", telegram_id).execute()
    if existing.data:
        return existing.data[0]
    result = sb.table("users").insert({
        "telegram_id": telegram_id,
        "name": name,
        "status": "unpaid",
    }).execute()
    return result.data[0] if result.data else {}


def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    result = _db().table("users").select("*").eq("telegram_id", telegram_id).execute()
    return result.data[0] if result.data else None


def get_all_users() -> List[Dict[str, Any]]:
    result = _db().table("users").select("*").order("joined_at").execute()
    return result.data or []


def get_unpaid_users() -> List[Dict[str, Any]]:
    result = _db().table("users").select("*").eq("status", "unpaid").execute()
    return result.data or []


def get_paid_users() -> List[Dict[str, Any]]:
    result = _db().table("users").select("*").eq("status", "paid").execute()
    return result.data or []


def update_user_name(telegram_id: int, new_name: str) -> bool:
    result = _db().table("users").update({
        "name": new_name,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("telegram_id", telegram_id).execute()
    return bool(result.data)


def update_user_status(telegram_id: int, status: str) -> bool:
    """status must be 'paid' or 'unpaid'."""
    result = _db().table("users").update({
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("telegram_id", telegram_id).execute()
    return bool(result.data)


def get_total_users_count() -> int:
    result = _db().table("users").select("id", count="exact").execute()
    return result.count or 0


def reset_all_users_to_unpaid() -> None:
    """Reset every user's status to 'unpaid'. Called at the start of a billing cycle."""
    _db().table("users").update({"status": "unpaid"}).neq("status", "").execute()


# ── Admin operations ──────────────────────────────────────────────────────────

def add_admin(telegram_id: int, added_by: int, is_super: bool = False) -> bool:
    try:
        _db().table("admins").upsert({
            "telegram_id": telegram_id,
            "is_super": is_super,
            "added_by": added_by,
        }, on_conflict="telegram_id").execute()
        return True
    except Exception as exc:
        logger.error(f"add_admin error: {exc}")
        return False


def remove_admin(telegram_id: int) -> bool:
    """Cannot remove a super admin."""
    result = (
        _db().table("admins")
        .delete()
        .eq("telegram_id", telegram_id)
        .eq("is_super", False)
        .execute()
    )
    return bool(result.data)


def get_all_admins() -> List[Dict[str, Any]]:
    result = _db().table("admins").select("*").execute()
    return result.data or []


def is_admin(telegram_id: int) -> bool:
    """Returns True for both regular admins and super admins."""
    if is_super_admin(telegram_id):
        return True
    result = _db().table("admins").select("id").eq("telegram_id", telegram_id).execute()
    return bool(result.data)


def is_super_admin(telegram_id: int) -> bool:
    """Returns True if the user is the env-configured super admin or a DB super admin."""
    if config.ADMIN_ID and telegram_id == config.ADMIN_ID:
        return True
    result = (
        _db().table("admins")
        .select("id")
        .eq("telegram_id", telegram_id)
        .eq("is_super", True)
        .execute()
    )
    return bool(result.data)


# ── Payment operations ────────────────────────────────────────────────────────

def create_payment_record(
    telegram_id: int,
    receipt_channel_msg_id: int,
    eth_month: int,
    eth_year: int,
    eth_payment_date: str = "",
) -> Dict[str, Any]:
    """
    Create a new pending payment record.
    month and year are Ethiopian calendar values.
    """
    result = _db().table("payments").insert({
        "telegram_id": telegram_id,
        "month": eth_month,
        "year": eth_year,
        "receipt_channel_msg_id": receipt_channel_msg_id,
        "status": "pending",
        "eth_payment_date": eth_payment_date,
    }).execute()
    return result.data[0] if result.data else {}


def get_pending_payments() -> List[Dict[str, Any]]:
    result = (
        _db().table("payments")
        .select("*")
        .eq("status", "pending")
        .order("created_at")
        .execute()
    )
    return result.data or []


def get_payment_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
    result = _db().table("payments").select("*").eq("id", payment_id).execute()
    return result.data[0] if result.data else None


def approve_payment(payment_id: int) -> bool:
    """Approve a payment and mark the user as paid."""
    payment = get_payment_by_id(payment_id)
    if not payment:
        return False
    _db().table("payments").update({
        "status": "approved",
        "reviewed_at": datetime.utcnow().isoformat(),
    }).eq("id", payment_id).execute()
    update_user_status(payment["telegram_id"], "paid")
    return True


def reject_payment(payment_id: int, reason: str) -> bool:
    """Reject a payment with a reason."""
    result = _db().table("payments").update({
        "status": "rejected",
        "rejected_reason": reason,
        "reviewed_at": datetime.utcnow().isoformat(),
    }).eq("id", payment_id).execute()
    return bool(result.data)


def get_user_payment_history(telegram_id: int) -> List[Dict[str, Any]]:
    result = (
        _db().table("payments")
        .select("*")
        .eq("telegram_id", telegram_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def get_monthly_payments(eth_month: int, eth_year: int) -> List[Dict[str, Any]]:
    """Return all approved payments for a given Ethiopian month/year."""
    result = (
        _db().table("payments")
        .select("*")
        .eq("month", eth_month)
        .eq("year", eth_year)
        .eq("status", "approved")
        .execute()
    )
    return result.data or []


def get_total_paid_this_month() -> int:
    """Return count of approved payments for the current Ethiopian month."""
    from utils import to_ethiopian, now_eth
    eth_year, eth_month, _ = to_ethiopian(now_eth())
    return len(get_monthly_payments(eth_month, eth_year))


def get_unpaid_users_for_month(eth_month: int, eth_year: int) -> List[Dict[str, Any]]:
    """Return all users who do NOT have an approved payment for the given Ethiopian month/year."""
    sb = _db()
    all_users = get_all_users()
    approved = (
        sb.table("payments")
        .select("telegram_id")
        .eq("month", eth_month)
        .eq("year", eth_year)
        .eq("status", "approved")
        .execute()
    )
    paid_ids = {r["telegram_id"] for r in (approved.data or [])}
    return [u for u in all_users if u["telegram_id"] not in paid_ids]


def get_attendance_data(eth_month: int, eth_year: int) -> List[Dict[str, Any]]:
    """
    Build a per-user attendance record for one billing cycle.

    Timeliness classification:
      ወቅቱን ጠብቆ (On Time) — paid with >=2 days before end day
      ዘግይቶ (Late)         — paid on last 1-2 days
      አልከፈለም (Unpaid)     — no approved payment found
    """
    from utils import eth_month_name

    all_users = get_all_users()
    approved = get_monthly_payments(eth_month, eth_year)

    payment_map: Dict[int, Dict[str, Any]] = {}
    for p in approved:
        tid = p["telegram_id"]
        if tid not in payment_map or p["created_at"] < payment_map[tid]["created_at"]:
            payment_map[tid] = p

    end_day = int(get_setting("billing_end_day", "5"))
    month_name = eth_month_name(eth_month)

    rows = []
    for u in all_users:
        tid = u["telegram_id"]
        p = payment_map.get(tid)

        if p:
            paid_at_str  = str(p.get("created_at", ""))[:10]
            paid_time_str = str(p.get("created_at", ""))[:16]
            try:
                paid_day = int(paid_at_str[8:10])
            except (ValueError, IndexError):
                paid_day = end_day

            timeliness = "ዘግይቶ" if paid_day >= end_day - 1 else "ወቅቱን ጠብቆ"
            timeliness_en = "Late" if timeliness == "ዘግይቶ" else "On Time"
            rows.append({
                "ተ.ቁ": 0,
                "ስም": u["name"],
                "Telegram ID": tid,
                "ወር": f"{month_name} {eth_year}",
                "ሁኔታ": "✅ ተከፍሏል",
                "ወቅታዊነት": timeliness,
                "Timeliness": timeliness_en,
                "የክፍያ ቀን": paid_time_str,
                "_sort": 0,
                "_timeliness_sort": 0 if timeliness_en == "On Time" else 1,
            })
        else:
            rows.append({
                "ተ.ቁ": 0,
                "ስም": u["name"],
                "Telegram ID": tid,
                "ወር": f"{month_name} {eth_year}",
                "ሁኔታ": "❌ አልተከፈለም",
                "ወቅታዊነት": "አልከፈለም",
                "Timeliness": "Unpaid",
                "የክፍያ ቀን": "—",
                "_sort": 1,
                "_timeliness_sort": 2,
            })

    rows.sort(key=lambda r: (r["_sort"], r["_timeliness_sort"], r["ስም"]))
    for i, row in enumerate(rows, 1):
        row["ተ.ቁ"] = i
        del row["_sort"]
        del row["_timeliness_sort"]

    return rows


def get_cycle_summary(eth_month: int, eth_year: int) -> Dict[str, Any]:
    """
    Return a full summary snapshot for a closing billing cycle.
    Call BEFORE resetting statuses so numbers are still accurate.
    """
    from utils import eth_month_name

    sb = _db()
    all_users   = get_all_users()
    approved    = get_monthly_payments(eth_month, eth_year)
    paid_ids    = {p["telegram_id"] for p in approved}
    paid_users  = [u for u in all_users if u["telegram_id"] in paid_ids]
    unpaid_users = [u for u in all_users if u["telegram_id"] not in paid_ids]

    pending_count = len(
        sb.table("payments")
        .select("id")
        .eq("month", eth_month)
        .eq("year", eth_year)
        .eq("status", "pending")
        .execute().data or []
    )
    rejected_count = len(
        sb.table("payments")
        .select("id")
        .eq("month", eth_month)
        .eq("year", eth_year)
        .eq("status", "rejected")
        .execute().data or []
    )

    return {
        "month":          eth_month,
        "year":           eth_year,
        "month_name":     eth_month_name(eth_month),
        "total_users":    len(all_users),
        "total_paid":     len(paid_users),
        "total_unpaid":   len(unpaid_users),
        "total_pending":  pending_count,
        "total_rejected": rejected_count,
        "paid_users":     paid_users,
        "unpaid_users":   unpaid_users,
    }


# ── Settings operations ───────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    result = _db().table("settings").select("value").eq("key", key).execute()
    return result.data[0]["value"] if result.data else default


def set_setting(key: str, value: str) -> bool:
    result = _db().table("settings").upsert(
        {"key": key, "value": value, "updated_at": datetime.utcnow().isoformat()},
        on_conflict="key",
    ).execute()
    return bool(result.data)


def get_all_settings() -> Dict[str, str]:
    result = _db().table("settings").select("*").execute()
    return {row["key"]: row["value"] for row in (result.data or [])}


def get_billing_cycle() -> Dict[str, int]:
    """Return {'start': int, 'end': int} using valid Ethiopian day range (1–30)."""
    try:
        start = int(get_setting("billing_start_day", "25"))
    except (ValueError, TypeError):
        start = 25
    try:
        end = int(get_setting("billing_end_day", "5"))
    except (ValueError, TypeError):
        end = 5
    start = start if 1 <= start <= 30 else 25
    end   = end   if 1 <= end   <= 30 else 5
    return {"start": start, "end": end}


# ── Bank account operations ───────────────────────────────────────────────────

def get_active_bank_accounts() -> List[Dict[str, Any]]:
    result = _db().table("bank_accounts").select("*").eq("is_active", True).execute()
    return result.data or []


def add_bank_account(bank_name: str, account_number: str, account_holder: str) -> bool:
    result = _db().table("bank_accounts").insert({
        "bank_name":      bank_name,
        "account_number": account_number,
        "account_holder": account_holder,
        "is_active":      True,
    }).execute()
    return bool(result.data)


def deactivate_bank_account(account_id: int) -> bool:
    result = _db().table("bank_accounts").update({"is_active": False}).eq("id", account_id).execute()
    return bool(result.data)


# ── Support message operations ────────────────────────────────────────────────

def create_support_message(telegram_id: int, message: str) -> Dict[str, Any]:
    result = _db().table("support_messages").insert({
        "telegram_id": telegram_id,
        "message":     message,
    }).execute()
    return result.data[0] if result.data else {}


def get_unanswered_support_messages() -> List[Dict[str, Any]]:
    result = (
        _db().table("support_messages")
        .select("*")
        .is_("reply", "null")
        .order("created_at")
        .execute()
    )
    return result.data or []


def reply_to_support_message(msg_id: int, reply: str, replied_by: int) -> bool:
    result = _db().table("support_messages").update({
        "reply":      reply,
        "replied_by": replied_by,
        "replied_at": datetime.utcnow().isoformat(),
    }).eq("id", msg_id).execute()
    return bool(result.data)


# ─────────────────────────────────────────────────────────────────────────────
#  REFERENCE SQL — run once in Supabase SQL editor to create tables
# ─────────────────────────────────────────────────────────────────────────────
#
# CREATE TABLE IF NOT EXISTS users (
#     id          BIGSERIAL PRIMARY KEY,
#     telegram_id BIGINT UNIQUE NOT NULL,
#     name        TEXT NOT NULL DEFAULT 'ያልታወቀ',
#     status      TEXT NOT NULL DEFAULT 'unpaid',
#     joined_at   TIMESTAMPTZ DEFAULT NOW(),
#     updated_at  TIMESTAMPTZ DEFAULT NOW()
# );
#
# CREATE TABLE IF NOT EXISTS admins (
#     id          BIGSERIAL PRIMARY KEY,
#     telegram_id BIGINT UNIQUE NOT NULL,
#     is_super    BOOLEAN DEFAULT FALSE,
#     added_by    BIGINT,
#     added_at    TIMESTAMPTZ DEFAULT NOW()
# );
#
# CREATE TABLE IF NOT EXISTS payments (
#     id                     BIGSERIAL PRIMARY KEY,
#     telegram_id            BIGINT NOT NULL,
#     month                  INT NOT NULL,
#     year                   INT NOT NULL,
#     receipt_channel_msg_id BIGINT,
#     status                 TEXT NOT NULL DEFAULT 'pending',
#     rejected_reason        TEXT,
#     eth_payment_date       TEXT,
#     created_at             TIMESTAMPTZ DEFAULT NOW(),
#     reviewed_at            TIMESTAMPTZ
# );
#
# CREATE TABLE IF NOT EXISTS settings (
#     key        TEXT PRIMARY KEY,
#     value      TEXT NOT NULL,
#     updated_at TIMESTAMPTZ DEFAULT NOW()
# );
#
# CREATE TABLE IF NOT EXISTS support_messages (
#     id          BIGSERIAL PRIMARY KEY,
#     telegram_id BIGINT NOT NULL,
#     message     TEXT NOT NULL,
#     reply       TEXT,
#     replied_by  BIGINT,
#     created_at  TIMESTAMPTZ DEFAULT NOW(),
#     replied_at  TIMESTAMPTZ
# );
#
# CREATE TABLE IF NOT EXISTS bank_accounts (
#     id              BIGSERIAL PRIMARY KEY,
#     bank_name       TEXT NOT NULL,
#     account_number  TEXT NOT NULL,
#     account_holder  TEXT NOT NULL,
#     is_active       BOOLEAN DEFAULT TRUE,
#     created_at      TIMESTAMPTZ DEFAULT NOW()
# );
