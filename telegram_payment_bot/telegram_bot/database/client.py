"""
database/client.py
───────────────────
Supabase data access layer.

FIXES applied:
 - register_user(): phone made optional (default "") so old call sites don't crash
 - get_total_paid_this_month(): fixed tuple unpacking (was using .year/.month on tuple)
 - create_payment_record(): added receipt_file_id parameter
 - Reference SQL updated: phone, username, receipt_file_id columns added
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.ethiopian_calendar import now_eth as _now_eat

from supabase import Client, create_client

import config

logger = logging.getLogger(__name__)

_supabase: Optional[Client] = None


def _db() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabase


# ── Schema bootstrap ──────────────────────────────────────────────────────────

def init_tables() -> None:
    _seed_default_settings()
    logger.info("Database: default settings seeded.")


def _seed_default_settings() -> None:
    from texts import T

    defaults: Dict[str, str] = {
        "billing_start_day":    "25",
        "billing_end_day":      "30",  # Same-month default: Ginbot 25 → Ginbot 30
        "msg_payment_start":    T.DEFAULT_MSG_PAYMENT_START,
        "msg_reminder_one_day": T.DEFAULT_MSG_ONE_DAY,
        "msg_final_day":        T.DEFAULT_MSG_FINAL_DAY,
        "msg_approved":         T.NOTIFY_APPROVED,
        "msg_rejected":         T.NOTIFY_REJECTED,
        "notify_payment_start":           "true",
        "notify_one_day":                 "true",
        "notify_final_day":               "true",
        "last_payment_start_eth_date":    "",   # set by send_payment_start_reminder
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
    while True:
        try:
            _db().table("settings").select("key").limit(1).execute()
            logger.info("Supabase keep-alive ping OK.")
        except Exception as exc:
            logger.error(f"Supabase ping failed: {exc}")
        await asyncio.sleep(48 * 3600)


# ── User operations ───────────────────────────────────────────────────────────

def register_user(
    telegram_id: int,
    name: str,
    phone: str = "",
    username: str = None,
) -> Dict[str, Any]:
    """
    Register a user if not already registered, or return the existing record.
    phone is optional — the new registration flow collects it separately.
    """
    sb = _db()
    existing = (
        sb.table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    result = sb.table("users").insert({
        "telegram_id": telegram_id,
        "name":        name,
        "phone":       phone,
        "username":    username,
        "status":      "unpaid",
    }).execute()

    return result.data[0] if result.data else {}


def complete_user_registration(
    telegram_id: int,
    name: str,
    phone: str,
    username: str = None,
) -> Dict[str, Any]:
    """Upsert full user record including phone. Used by the registration conversation."""
    result = _db().table("users").upsert(
        {
            "telegram_id": telegram_id,
            "name":        name,
            "phone":       phone,
            "username":    username,
            "status":      "unpaid",
        },
        on_conflict="telegram_id",
    ).execute()
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
        "name":       new_name,
        "updated_at": _now_eat().isoformat(),
    }).eq("telegram_id", telegram_id).execute()
    return bool(result.data)


def update_user_phone(telegram_id: int, phone: str) -> bool:
    result = _db().table("users").update({
        "phone":      phone,
        "updated_at": _now_eat().isoformat(),
    }).eq("telegram_id", telegram_id).execute()
    return bool(result.data)


def update_user_status(telegram_id: int, status: str) -> bool:
    result = _db().table("users").update({
        "status":     status,
        "updated_at": _now_eat().isoformat(),
    }).eq("telegram_id", telegram_id).execute()
    return bool(result.data)


def get_total_users_count() -> int:
    result = _db().table("users").select("id", count="exact").execute()
    return result.count or 0


def reset_all_users_to_unpaid() -> None:
    _db().table("users").update({"status": "unpaid"}).neq("status", "").execute()


# ── Admin operations ──────────────────────────────────────────────────────────

def add_admin(telegram_id: int, added_by: int, is_super: bool = False) -> bool:
    try:
        _db().table("admins").upsert({
            "telegram_id": telegram_id,
            "is_super":    is_super,
            "added_by":    added_by,
        }, on_conflict="telegram_id").execute()
        return True
    except Exception as exc:
        logger.error(f"add_admin error: {exc}")
        return False


def remove_admin(telegram_id: int) -> bool:
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
    """Returns True for both regular and super admins. Uses a single DB query."""
    if config.ADMIN_ID and telegram_id == config.ADMIN_ID:
        return True
    result = _db().table("admins").select("id").eq("telegram_id", telegram_id).execute()
    return bool(result.data)


def is_super_admin(telegram_id: int) -> bool:
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
    receipt_file_id: str = "",
) -> Dict[str, Any]:
    """
    Create a new pending payment record.
    receipt_file_id stores the Telegram file_id so admins can view the photo.
    """
    result = _db().table("payments").insert({
        "telegram_id":             telegram_id,
        "month":                   eth_month,
        "year":                    eth_year,
        "receipt_channel_msg_id":  receipt_channel_msg_id,
        "receipt_file_id":         receipt_file_id,
        "status":                  "pending",
        "eth_payment_date":        eth_payment_date,
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
    payment = get_payment_by_id(payment_id)
    if not payment:
        return False
    _db().table("payments").update({
        "status":      "approved",
        "reviewed_at": _now_eat().isoformat(),
    }).eq("id", payment_id).execute()
    update_user_status(payment["telegram_id"], "paid")
    return True


def reject_payment(payment_id: int, reason: str) -> bool:
    result = _db().table("payments").update({
        "status":          "rejected",
        "rejected_reason": reason,
        "reviewed_at":     _now_eat().isoformat(),
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


def has_pending_or_approved_payment(telegram_id: int, eth_month: int, eth_year: int) -> bool:
    """Check whether user already has a pending or approved payment for this month."""
    result = (
        _db().table("payments")
        .select("id")
        .eq("telegram_id", telegram_id)
        .eq("month", eth_month)
        .eq("year", eth_year)
        .in_("status", ["pending", "approved"])
        .execute()
    )
    return bool(result.data)


def get_monthly_payments(eth_month: int, eth_year: int) -> List[Dict[str, Any]]:
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
    """Return count of approved payments for the current Ethiopian month.
    FIX: was using .year/.month attribute access on tuple return value.
    """
    from utils import to_ethiopian, now_eth
    eth_year, eth_month, _ = to_ethiopian(now_eth())
    return len(get_monthly_payments(eth_month, eth_year))


def get_unpaid_users_for_month(eth_month: int, eth_year: int) -> List[Dict[str, Any]]:
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
    Build per-user attendance record for one billing cycle.
    FIX: timeliness now uses Ethiopian day extracted from eth_payment_date field,
    not the raw Gregorian created_at day.
    """
    from utils import eth_month_name

    all_users  = get_all_users()
    approved   = get_monthly_payments(eth_month, eth_year)

    payment_map: Dict[int, Dict[str, Any]] = {}
    for p in approved:
        tid = p["telegram_id"]
        if tid not in payment_map or p["created_at"] < payment_map[tid]["created_at"]:
            payment_map[tid] = p

    end_day    = int(get_setting("billing_end_day", "5"))
    month_name = eth_month_name(eth_month)

    rows = []
    for u in all_users:
        tid = u["telegram_id"]
        p   = payment_map.get(tid)

        if p:
            eth_date_str = p.get("eth_payment_date", "")

            # Use stored Ethiopian payment day for timeliness — not Gregorian day
            try:
                eth_day_paid = int(eth_date_str.split("-")[2]) if eth_date_str else end_day
            except (IndexError, ValueError):
                eth_day_paid = end_day

            timeliness    = "ዘግይቶ" if eth_day_paid >= end_day - 1 else "ወቅቱን ጠብቆ"
            timeliness_en = "Late" if timeliness == "ዘግይቶ" else "On Time"

            # Convert stored Ethiopian date "2018-09-28" → "28 ግንቦት 2018" for display.
            # Never use created_at (Gregorian UTC timestamp) in user-facing reports.
            from utils.ethiopian_calendar import eth_storage_to_display
            payment_date_display = eth_storage_to_display(eth_date_str)

            rows.append({
                "ተ.ቁ":         0,
                "ስም":          u["name"],
                "Telegram ID": tid,
                "ወር":          f"{month_name} {eth_year}",
                "ሁኔታ":        "✅ ተከፍሏል",
                "ወቅታዊነት":     timeliness,
                "Timeliness":  timeliness_en,
                "የክፍያ ቀን":    payment_date_display,
                "_sort":              0,
                "_timeliness_sort":   0 if timeliness_en == "On Time" else 1,
            })
        else:
            rows.append({
                "ተ.ቁ":         0,
                "ስም":          u["name"],
                "Telegram ID": tid,
                "ወር":          f"{month_name} {eth_year}",
                "ሁኔታ":        "❌ አልተከፈለም",
                "ወቅታዊነት":     "አልከፈለም",
                "Timeliness":  "Unpaid",
                "የክፍያ ቀን":    "—",
                "_sort":             1,
                "_timeliness_sort":  2,
            })

    rows.sort(key=lambda r: (r["_sort"], r["_timeliness_sort"], r["ስም"]))
    for i, row in enumerate(rows, 1):
        row["ተ.ቁ"] = i
        del row["_sort"]
        del row["_timeliness_sort"]

    return rows


def get_cycle_summary(eth_month: int, eth_year: int) -> Dict[str, Any]:
    from utils import eth_month_name

    sb         = _db()
    all_users  = get_all_users()
    approved   = get_monthly_payments(eth_month, eth_year)
    paid_ids   = {p["telegram_id"] for p in approved}
    paid_users = [u for u in all_users if u["telegram_id"] in paid_ids]
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
        {"key": key, "value": value, "updated_at": _now_eat().isoformat()},
        on_conflict="key",
    ).execute()
    return bool(result.data)


def get_all_settings() -> Dict[str, str]:
    result = _db().table("settings").select("*").execute()
    return {row["key"]: row["value"] for row in (result.data or [])}


def get_billing_cycle() -> Dict[str, int]:
    try:
        start = int(get_setting("billing_start_day", "25"))
    except (ValueError, TypeError):
        start = 25
    try:
        end = int(get_setting("billing_end_day", "30"))  # default same-month: 25→30
    except (ValueError, TypeError):
        end = 30
    start = start if 1 <= start <= 30 else 25
    end   = end   if 1 <= end   <= 30 else 30
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


def get_support_message_by_id(msg_id: int) -> Optional[Dict[str, Any]]:
    result = _db().table("support_messages").select("*").eq("id", msg_id).execute()
    return result.data[0] if result.data else None


def reply_to_support_message(msg_id: int, reply: str, replied_by: int) -> bool:
    result = _db().table("support_messages").update({
        "reply":      reply,
        "replied_by": replied_by,
        "replied_at": _now_eat().isoformat(),
    }).eq("id", msg_id).execute()
    return bool(result.data)


# ─────────────────────────────────────────────────────────────────────────────
#  REFERENCE SQL — run once in Supabase SQL editor
#  UPDATED: added phone, username to users; added receipt_file_id to payments
# ─────────────────────────────────────────────────────────────────────────────
#
# CREATE TABLE IF NOT EXISTS users (
#     id          BIGSERIAL PRIMARY KEY,
#     telegram_id BIGINT UNIQUE NOT NULL,
#     name        TEXT NOT NULL DEFAULT 'ያልታወቀ',
#     phone       TEXT NOT NULL DEFAULT '',
#     username    TEXT,
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
#     receipt_file_id        TEXT DEFAULT '',
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
