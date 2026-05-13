"""
config.py
─────────
Central configuration loader. All values come from environment variables.
Never hard-code secrets here — use the .env file locally.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. Check your .env file."
        )
    return value


# ─── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN: str = _require("TELEGRAM_TOKEN")

# ─── Super Admin ───────────────────────────────────────────────────────────────
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

# ─── Receipt Channel ───────────────────────────────────────────────────────────
# Numeric chat ID of the channel/group where payment screenshots are forwarded.
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "").strip()

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
