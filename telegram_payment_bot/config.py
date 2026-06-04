"""
config.py
─────────
Central configuration loader. All values come from environment variables.
Never hard-code secrets here — use the .env file locally or Replit Secrets.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set.\n"
            f"Check your .env file or Replit Secrets panel."
        )
    return value


def _optional_int(key: str, default: int = 0) -> int:
    val = os.getenv(key, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        logging.getLogger(__name__).warning(
            f"Env var '{key}' = '{val}' is not a valid integer; using default {default}."
        )
        return default


# ─── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN: str = _require("TELEGRAM_TOKEN")

# ─── Super Admin ───────────────────────────────────────────────────────────────
ADMIN_ID: int = _optional_int("ADMIN_ID", 0)

# ─── Receipt Channel ───────────────────────────────────────────────────────────
# Private Telegram channel used for receipt storage AND file archiving (Phase 3).
# Must be the numeric chat ID (e.g. -1001234567890).
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "").strip()

# ─── Storage Channel ───────────────────────────────────────────────────────────
# Secondary private channel for large file storage (Phase 3).
# If not set, falls back to CHANNEL_ID.
STORAGE_CHANNEL_ID: str = os.getenv("STORAGE_CHANNEL_ID", CHANNEL_ID).strip()

# ─── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL: str = _require("SUPABASE_URL")
SUPABASE_KEY: str = _require("SUPABASE_KEY")

# ─── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: str = os.getenv("LOG_FILE", "./logs/bot.log")


def setup_logging() -> None:
    """Configure root logger. Call once at startup."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def validate() -> None:
    """
    Run at startup to catch misconfiguration early.
    Logs warnings for optional-but-important settings.
    """
    log = logging.getLogger(__name__)
    if not ADMIN_ID:
        log.warning("ADMIN_ID not set — no super admin will be seeded.")
    if not CHANNEL_ID:
        log.warning(
            "CHANNEL_ID not set — payment screenshots cannot be forwarded to admins."
        )
    if not STORAGE_CHANNEL_ID:
        log.warning(
            "STORAGE_CHANNEL_ID not set — secondary Telegram storage disabled."
        )
