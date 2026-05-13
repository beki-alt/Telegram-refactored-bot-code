# Telegram Payment Bot — Refactored

A production-quality Telegram subscription payment management bot with full Amharic UI and Ethiopian calendar support.

## What Changed From the Original

| Area | Original | Refactored |
|---|---|---|
| Card system | Generates membership card images | **Removed completely** |
| Amharic text | Scattered across every file | **All centralized in `texts.py`** |
| Architecture | 4 monolithic files | **Modular folders** |
| get_total_paid_this_month | Used Gregorian month | **Fixed — uses Ethiopian month** |
| Code quality | Duplicated logic, inconsistent | **Clean, DRY, commented** |

## Project Structure

```
telegram_payment_bot/
├── main.py                 ← Entry point
├── config.py               ← Environment variable loader
├── texts.py                ← ALL Amharic strings (single source of truth)
├── keep_alive.py           ← Flask server for deployment keep-alive
├── requirements.txt
├── .env.example
│
├── utils/
│   └── ethiopian_calendar.py  ← Ethiopian date conversion + helpers
│
├── database/
│   └── client.py           ← All Supabase operations
│
├── keyboards/
│   ├── user_keyboards.py   ← Reply + inline keyboards for users
│   └── admin_keyboards.py  ← All admin panel keyboards
│
├── handlers/               ← User-facing conversation handlers
│   ├── start.py            ← /start command
│   ├── profile.py          ← 👤 My Profile (edit name)
│   ├── payment.py          ← 💳 Pay/Renew + 📅 Schedule
│   ├── support.py          ← 📝 Support & History
│   └── common.py           ← Shared cancel handler
│
├── admin/                  ← Admin panel
│   ├── panel.py            ← Main panel + top-level navigation
│   ├── management.py       ← Add/remove/list admins
│   ├── settings.py         ← Messages, notifications, billing cycle, banks
│   ├── users.py            ← View users, debtors, manual edit
│   ├── inbox.py            ← Receipt approval, support replies, broadcast
│   ├── reports.py          ← Quick reports + Excel exports + notify unpaid
│   ├── reminders.py        ← Automated JobQueue reminder tasks
│   └── conversation.py     ← Master ConversationHandler builder
│
└── middleware/
    └── auth.py             ← @admin_required / @super_admin_required decorators
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file
```bash
cp .env.example .env
# Edit .env with your real values
```

Required environment variables:

| Variable | Description |
|---|---|
| `TELEGRAM_TOKEN` | Bot token from @BotFather |
| `ADMIN_ID` | Your personal Telegram numeric ID |
| `CHANNEL_ID` | Chat/channel ID for payment receipt forwarding (e.g. `-1001234567890`) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase service key |

### 3. Create Supabase tables
Copy the SQL at the bottom of `database/client.py` and run it once in the Supabase SQL editor.

### 4. Run the bot
```bash
python main.py
```

## How to change Amharic text

Open `texts.py` and edit any string. **Do not put Amharic text anywhere else.**

Example:
```python
# texts.py
class T:
    WELCOME = "👋 *እንኳን ደህና መጡ, {name}!*\n\n..."
```

## Features

- **User flow**: register → view profile → edit name → submit payment screenshot → track history
- **Payment workflow**: user uploads photo → forwarded to admin channel → admin approves/rejects → user notified
- **Admin panel**: approve/reject receipts, edit message templates, manage bank accounts, manage billing cycle dates, broadcast messages, view Excel reports
- **Ethiopian calendar**: all dates (profile join date, payment dates, reports, reminders) use Ethiopian calendar
- **Automated reminders**: billing start, one-day-before, final-day — all via JobQueue at noon Ethiopian time
- **Monthly reset**: automatic cycle close report sent to all admins + users reset to unpaid

## Architecture Decisions

- **Supabase**: kept as the database backend (existing schema preserved, no card-related columns needed)
- **texts.py**: single class `T` with all Amharic strings as class attributes — change once, applies everywhere
- **Ethiopian calendar**: built-in JDN algorithm with optional `ethiopian-date` library fallback
- **No card system**: `image_gen.py` and all card references have been removed entirely
- **Middleware decorators**: `@admin_required` and `@super_admin_required` keep auth logic out of handlers
