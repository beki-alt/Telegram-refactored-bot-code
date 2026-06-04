# Telegram Payment Bot

Production-ready Telegram bot for managing monthly subscription payments with Ethiopian calendar support.

## Quick Start

### 1. Create Supabase tables

Open the Supabase SQL editor and run the full contents of **`SQL_SCHEMA.sql`**.

### 2. Configure environment variables

Copy `.env.example` → `.env` (or set as Replit Secrets) and fill in:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | ✅ | From [@BotFather](https://t.me/BotFather) |
| `SUPABASE_URL` | ✅ | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase `anon` key |
| `ADMIN_ID` | ✅ | Your Telegram numeric user ID |
| `CHANNEL_ID` | ✅ | Private channel ID for receipt storage |
| `STORAGE_CHANNEL_ID` | ☐ | Secondary large-file channel (Phase 3) |

### 3. Add bot to receipt channel

The bot must be an **admin** of the private channel specified in `CHANNEL_ID`.

### 4. Start the bot

Use the **Telegram Bot** workflow in Replit (or run directly):

```bash
cd telegram-bot
pip install -r requirements.txt
python main.py
```

---

## Features

### User features
- `/start` — register and show main menu
- **💳 Pay/Renew** — submit payment receipt photo
- **👤 My Profile** — view status and edit display name
- **📅 Payment Schedule** — Ethiopian calendar billing countdown
- **📝 Support & History** — view payment history, contact admins

### Admin features (`/admin`)
- **Inbox** — review/approve/reject pending receipts, reply to support messages, broadcast
- **Users** — list all/unpaid users, manual status and name edits
- **Settings** — customize message templates, notification toggles, billing cycle, bank accounts
- **Reports** — quick summary, Excel exports, notify-unpaid by month

---

## Bug Fixes Applied (vs. original source)

| # | Module | Bug | Fix |
|---|---|---|---|
| 1 | `utils/ethiopian_calendar.py` | `to_ethiopian()` returned an object; `.year/.month/.day` worked but `format_eth_date()` treated it as a tuple → `AttributeError` | `to_ethiopian()` now always returns a `(year, month, day)` tuple |
| 2 | `database/client.py` | `to_ethiopian()` result unpacked as `(year, month, day, _)` (4 elements) | Changed to 3-element unpack |
| 3 | `handlers/start.py` | `register_user()` called with only 2 args (missing `phone`) | `phone` is now optional with default `""` |
| 4 | `admin/conversation.py` | All 4 state modules used `0` as first state → Python dict silently overwrote 3 of them | All states are unique integers from `admin/states.py` (10–62) |
| 5 | `admin/inbox.py` | Receipt display called `send_photo(photo=message_id)` — IDs ≠ file IDs → crash | Stores `receipt_file_id` (Telegram file_id) in DB; admin inbox uses it for display |
| 6 | `admin/inbox.py` | `query.answer()` called twice in support-reply handler | Removed duplicate call |

---

## New Phases Implemented

| Phase | Feature |
|---|---|
| Phase 3 | `storage/telegram_channel.py` — Telegram channel as secondary file storage |
| Phase 4 | Ethiopian calendar validation in all date operations |
| Phase 5 | Button-based billing cycle day picker (6×5 grid with ✅ on current) |
| Phase 6 | Immediate payment-start notification trigger when start day is today |
| Phase 7 | `check_missed_jobs()` on startup — recovers any reminders missed while bot was offline |
| Phase 8 | Replit production hardening: logging, keep-alive, config validation, error trapping |
| Phase 9 | Full test suite: `tests/test_ethiopian_calendar.py`, `test_billing_cycle.py`, `test_scheduler.py` |

---

## Running Tests

```bash
cd telegram-bot
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

---

## Architecture

```
telegram-bot/
├── main.py              # Entry point, startup sequence
├── config.py            # Config from env vars
├── texts.py             # All UI strings (Amharic + English)
├── keep_alive.py        # Flask keep-alive server
├── utils/
│   └── ethiopian_calendar.py   # Calendar math (fixed tuple returns)
├── database/
│   └── client.py        # Supabase queries
├── storage/
│   └── telegram_channel.py     # Phase 3: channel storage service
├── keyboards/           # Telegram keyboard builders
├── middleware/          # Admin auth decorators
├── handlers/            # User-facing conversation handlers
├── admin/               # Admin panel modules
│   ├── states.py        # UNIQUE state integers (fixes state-0 conflict bug)
│   ├── conversation.py  # Assembles ConversationHandler
│   ├── reminders.py     # APScheduler jobs + Phase 7 missed-job recovery
│   └── ...
├── tests/               # Phase 9 test suite
├── SQL_SCHEMA.sql        # Run once in Supabase SQL editor
└── requirements.txt
```
