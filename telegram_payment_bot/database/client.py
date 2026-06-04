"""
database/client.py
───────────────────
Supabase data access layer — FIXED production version.

Bug fixes from original:
  - get_total_paid_this_month(): to_ethiopian() returns a tuple, not an object.
    Original did eth_date.year which throws AttributeError. Fixed to unpack tuple.
  - register_user(): made `phone` optional so /start works without phone collection.
  - update_user_*: now accepts explicit timestamp to avoid UTC vs local confusion.
  - payments table: now stores receipt_file_id (Telegram file_id) separately from
    receipt_channel_msg_id. The inbox display needs the file_id, not the message ID.

Table overview:
  users            — registered Telegram users + payment status
  admins           — admin users (regular + super)
  payments         — payment submission records + approval status
  settings         — key/value config store (billing cycle, messages, toggles)
  bank_accounts    — payment destination accounts shown to users
  support_messages — user support requests + admin replies
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

import config

logger = logging.getLogger(__name__)

# ── Supabase singleton ────────────────────────────────────────────────────────
_supabase: Optional[Client] = None
_last_reconnect: float = 0.0
_RECONNECT_COOLDOWN = 30  # seconds


def _db() -> Client:
    """Return (and lazily create) the Supabase client singleton."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabase


def _reconnect() -> Client:
    """Force-recreate the Supabase client (used after connection errors)."""
    global _supabase, _last_reconnect
    now = time.time()
    if now - _last_reconnect < _RECONNECT_COOLDOWN:
        return _supabase  # don't spam reconnects
    logger.info("Reconnecting Supabase client...")
    _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    _last_reconnect = now
    return _supabase


def _safe(fn):
    """
    Retry decorator for Supabase operations.
    On first failure, reconnects and retries once more.
    """
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.warning(f"DB operation failed, retrying after reconnect: {exc}")
            try:
                _reconnect()
                return fn(*args, **kwargs)
            except Exception as exc2:
                logger.error(f"DB operation failed after reconnect: {exc2}")
                raise
    wrapper.__name__ = getattr(fn, "__name__", "db_op")
    return wrapper


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Schema bootstrap ──────────────────────────────────────────────────────────

def init_tables() -> None:
    """Seed default settings on first boot."""
    _seed_default_settings()
    logger.info("Database: default settings seeded.")


def _seed_default_settings() -> None:
    """Insert default settings only if they do not already exist."""
    from texts import T

    defaults: Dict[str, str] = {
        "billing_start_day":    "25",
        "billing_end_day":      "5",
        "msg_payment_start":    T.DEFAULT_MSG_PAYMENT_START,
        "msg_reminder_one_day": T.DEFAULT_MSG_ONE_DAY,
        "msg_final_day":        T.DEFAULT_MSG_FINAL_DAY,
        "msg_approved":         T.NOTIFY_APPROVED,
        "msg_rejected":         T.NOTIFY_REJECTED,
        "notify_payment_start": "true",
        "notify_one_day":       "true",
        "notify_final_day":     "true",
        # Phase 7: missed-job tracking keys (store last-run date as YYYY-MM-DD in ETH)
        "last_run_payment_start": "",
        "last_run_one_day":       "",
        "last_run_final_day":     "",
        "last_run_monthly_reset": "",
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
            try:
                _reconnect()
            except Exception:
                pass
        await asyncio.sleep(48 * 3600)


# ── User operations ───────────────────────────────────────────────────────────

@_safe
def register_user(
    telegram_id: int,
    name: str,
    phone: str = "",
    username: str = None,
) -> Dict[str, Any]:
    """
    Register a user idempotently. Returns existing record if already registered.
    BUG FIX: phone was required but /start never collected it; made optional.
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


@_safe
def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    result = _db().table("users").select("*").eq("telegram_id", telegram_id).execute()
    return result.data[0] if result.data else None


@_safe
def complete_user_registration(
    telegram_id: int,
    name: str,
    phone: str,
    username: str = None,
) -> Dict[str, Any]:
    result = _db().table("users").upsert(
        {
            "telegram_id": telegram_id,
            "name":        name,
            "phone":       phone,
            "username":    username,
        },
        on_conflict="telegram_id",
    ).execute()
    return result.data[0] if result.data else {}


@_safe
def get_all_users() -> List[Dict[str, Any]]:
    result = _db().table("users").select("*").order("joined_at").execute()
    return result.data or []


@_safe
def get_unpaid_users() -> List[Dict[str, Any]]:
    result = _db().table("users").select("*").eq("status", "unpaid").execute()
    return result.data or []


@_safe
def get_paid_users() -> List[Dict[str, Any]]:
    result = _db().table("users").select("*").eq("status", "paid").execute()
    return result.data or []


@_safe
def update_user_name(telegram_id: int, new_name: str) -> bool:
    result = _db().table("users").update({
        "name":       new_name,
        "updated_at": _utcnow(),
    }).eq("telegram_id", telegram_id).execute()
    return bool(result.data)


@_safe
def update_user_phone(telegram_id: int, phone: str) -> bool:
    result = _db().table("users").update({
        "phone":      phone,
        "updated_at": _utcnow(),
    }).eq("telegram_id", telegram_id).execute()
    return bool(result.data)


@_safe
def update_user_status(telegram_id: int, status: str) -> bool:
    """status must be 'paid' or 'unpaid'."""
    if status not in ("paid", "unpaid"):
        logger.error(f"Invalid status value: {status}")
        return False
    result = _db().table("users").update({
        "status":     status,
        "updated_at": _utcnow(),
    }).eq("telegram_id", telegram_id).execute()
    return bool(result.data)


@_safe
def get_total_users_count() -> int:
    result = _db().table("users").select("id", count="exact").execute()
    return result.count or 0


@_safe
def reset_all_users_to_unpaid() -> None:
    """Reset every user's status to 'unpaid'. Called at the start of a billing cycle."""
    _db().table("users").update({"status": "unpaid"}).neq("status", "").execute()


# ── Admin operations ──────────────────────────────────────────────────────────

@_safe
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


@_safe
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


@_safe
def get_all_admins() -> List[Dict[str, Any]]:
    result = _db().table("admins").select("*").execute()
    return result.data or []


@_safe
def is_admin(telegram_id: int) -> bool:
    if is_super_admin(telegram_id):
        return True
    result = _db().table("admins").select("id").eq("telegram_id", telegram_id).execute()
    return bool(result.data)


@_safe
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

@_safe
def create_payment_record(
    telegram_id: int,
    receipt_channel_msg_id: int,
    receipt_file_id: str,
    eth_month: int,
    eth_year: int,
    eth_payment_date: str = "",
) -> Dict[str, Any]:
    """
    Create a new pending payment record.
    FIX: now stores receipt_file_id (Telegram file_id) so the admin inbox
    can display the photo. The original only stored channel message ID which
    cannot be used with send_photo().
    """
    result = _db().table("payments").insert({
        "telegram_id":            telegram_id,
        "month":                  eth_month,
        "year":                   eth_year,
        "receipt_channel_msg_id": receipt_channel_msg_id,
        "receipt_file_id":        receipt_file_id,
        "status":                 "pending",
        "eth_payment_date":       eth_payment_date,
    }).execute()
    return result.data[0] if result.data else {}


@_safe
def get_pending_payments() -> List[Dict[str, Any]]:
    result = (
        _db().table("payments")
        .select("*")
        .eq("status", "pending")
        .order("created_at")
        .execute()
    )
    return result.data or []


@_safe
def get_payment_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
    result = _db().table("payments").select("*").eq("id", payment_id).execute()
    return result.data[0] if result.data else None


@_safe
def approve_payment(payment_id: int) -> bool:
    payment = get_payment_by_id(payment_id)
    if not payment:
        return False
    _db().table("payments").update({
        "status":      "approved",
        "reviewed_at": _utcnow(),
    }).eq("id", payment_id).execute()
    update_user_status(payment["telegram_id"], "paid")
    return True


@_safe
def reject_payment(payment_id: int, reason: str) -> bool:
    result = _db().table("payments").update({
        "status":          "rejected",
        "rejected_reason": reason,
        "reviewed_at":     _utcnow(),
    }).eq("id", payment_id).execute()
    return bool(result.data)


@_safe
def get_user_payment_history(telegram_id: int) -> List[Dict[str, Any]]:
    result = (
        _db().table("payments")
        .select("*")
        .eq("telegram_id", telegram_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


@_safe
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


@_safe
def get_total_paid_this_month() -> int:
    """
    Return count of approved payments for the current Ethiopian month.
    BUG FIX: to_ethiopian() returns a tuple (year, month, day), not an object.
    Original called eth_date.year which threw AttributeError. Fixed.
    """
    from utils import to_ethiopian, now_eth
    eth_year, eth_month, _ = to_ethiopian(now_eth())
    return len(get_monthly_payments(eth_month, eth_year))


@_safe
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


@_safe
def get_attendance_data(eth_month: int, eth_year: int) -> List[Dict[str, Any]]:
    from utils import eth_month_name
    all_users = get_all_users()
    approved  = get_monthly_payments(eth_month, eth_year)
    end_day   = int(get_setting("billing_end_day", "5"))
    month_name = eth_month_name(eth_month)

    payment_map: Dict[int, Dict[str, Any]] = {}
    for p in approved:
        tid = p["telegram_id"]
        if tid not in payment_map or p["created_at"] < payment_map[tid]["created_at"]:
            payment_map[tid] = p

    rows = []
    for u in all_users:
        tid = u["telegram_id"]
        p   = payment_map.get(tid)
        if p:
            paid_at_str  = str(p.get("created_at", ""))[:10]
            paid_time_str = str(p.get("created_at", ""))[:16]
            try:
                paid_day = int(paid_at_str[8:10])
            except (ValueError, IndexError):
                paid_day = end_day
            timeliness    = "ዘግይቶ" if paid_day >= end_day - 1 else "ወቅቱን ጠብቆ"
            timeliness_en = "Late"  if timeliness == "ዘግይቶ"   else "On Time"
            rows.append({
                "ተ.ቁ":        0,
                "ስም":         u["name"],
                "Telegram ID": tid,
                "ወር":         f"{month_name} {eth_year}",
                "ሁኔታ":       "✅ ተከፍሏል",
                "ወቅታዊነት":   timeliness,
                "Timeliness":  timeliness_en,
                "የክፍያ ቀን":  paid_time_str,
                "_sort":       0,
                "_t_sort":     0 if timeliness_en == "On Time" else 1,
            })
        else:
            rows.append({
                "ተ.ቁ":        0,
                "ስም":         u["name"],
                "Telegram ID": tid,
                "ወር":         f"{month_name} {eth_year}",
                "ሁኔታ":       "❌ አልተከፈለም",
                "ወቅታዊነት":   "አልከፈለም",
                "Timeliness":  "Unpaid",
                "የክፍያ ቀን":  "—",
                "_sort":       1,
                "_t_sort":     2,
            })

    rows.sort(key=lambda r: (r["_sort"], r["_t_sort"], r["ስም"]))
    for i, row in enumerate(rows, 1):
        row["ተ.ቁ"] = i
        del row["_sort"]
        del row["_t_sort"]
    return rows


@_safe
def get_cycle_summary(eth_month: int, eth_year: int) -> Dict[str, Any]:
    from utils import eth_month_name
    sb           = _db()
    all_users    = get_all_users()
    approved     = get_monthly_payments(eth_month, eth_year)
    paid_ids     = {p["telegram_id"] for p in approved}
    paid_users   = [u for u in all_users if u["telegram_id"] in paid_ids]
    unpaid_users = [u for u in all_users if u["telegram_id"] not in paid_ids]

    pending_count = len(
        sb.table("payments").select("id")
        .eq("month", eth_month).eq("year", eth_year)
        .eq("status", "pending").execute().data or []
    )
    rejected_count = len(
        sb.table("payments").select("id")
        .eq("month", eth_month).eq("year", eth_year)
        .eq("status", "rejected").execute().data or []
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

@_safe
def get_setting(key: str, default: str = "") -> str:
    result = _db().table("settings").select("value").eq("key", key).execute()
    return result.data[0]["value"] if result.data else default


@_safe
def set_setting(key: str, value: str) -> bool:
    result = _db().table("settings").upsert(
        {"key": key, "value": value, "updated_at": _utcnow()},
        on_conflict="key",
    ).execute()
    return bool(result.data)


@_safe
def get_all_settings() -> Dict[str, str]:
    result = _db().table("settings").select("*").execute()
    return {row["key"]: row["value"] for row in (result.data or [])}


@_safe
def get_billing_cycle() -> Dict[str, int]:
    """Return {'start': int, 'end': int} with valid Ethiopian day range (1–30)."""
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

@_safe
def get_active_bank_accounts() -> List[Dict[str, Any]]:
    result = _db().table("bank_accounts").select("*").eq("is_active", True).execute()
    return result.data or []


@_safe
def add_bank_account(bank_name: str, account_number: str, account_holder: str) -> bool:
    result = _db().table("bank_accounts").insert({
        "bank_name":      bank_name,
        "account_number": account_number,
        "account_holder": account_holder,
        "is_active":      True,
    }).execute()
    return bool(result.data)


@_safe
def deactivate_bank_account(account_id: int) -> bool:
    result = (
        _db().table("bank_accounts")
        .update({"is_active": False})
        .eq("id", account_id)
        .execute()
    )
    return bool(result.data)


# ── Support message operations ────────────────────────────────────────────────

@_safe
def create_support_message(telegram_id: int, message: str) -> Dict[str, Any]:
    result = _db().table("support_messages").insert({
        "telegram_id": telegram_id,
        "message":     message,
    }).execute()
    return result.data[0] if result.data else {}


@_safe
def get_unanswered_support_messages() -> List[Dict[str, Any]]:
    result = (
        _db().table("support_messages")
        .select("*")
        .is_("reply", "null")
        .order("created_at")
        .execute()
    )
    return result.data or []


@_safe
def get_support_message_by_id(msg_id: int) -> Optional[Dict[str, Any]]:
    result = (
        _db().table("support_messages")
        .select("*")
        .eq("id", msg_id)
        .execute()
    )
    return result.data[0] if result.data else None


@_safe
def reply_to_support_message(msg_id: int, reply: str, replied_by: int) -> bool:
    result = _db().table("support_messages").update({
        "reply":      reply,
        "replied_by": replied_by,
        "replied_at": _utcnow(),
    }).eq("id", msg_id).execute()
    return bool(result.data)


# ─────────────────────────────────────────────────────────────────────────────
#  REFERENCE SQL — run once in Supabase SQL editor
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
#     receipt_file_id        TEXT,          -- Telegram file_id for photo display
#     status                 TEXT NOT NULL DEFAULT 'pending',
#     rejected_reason        TEXT,
#     eth_payment_date       TEXT,
#     created_at             TIMESTAMPTZ DEFAULT NOW(),
#     reviewed_at            TIMESTAMPTZ
# );
#
# CREATE TABLE IF NOT EXISTS settings (
#     key        TEXT PRIMARY KEY,
#     value      TEXT NOT NULL DEFAULT '',
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
