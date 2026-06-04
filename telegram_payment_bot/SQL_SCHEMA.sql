-- ============================================================
-- Telegram Payment Bot — Supabase SQL Schema
-- Run this once in the Supabase SQL editor before starting the bot.
-- ============================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    name        TEXT NOT NULL DEFAULT 'ያልታወቀ',
    phone       TEXT NOT NULL DEFAULT '',
    username    TEXT,
    status      TEXT NOT NULL DEFAULT 'unpaid' CHECK (status IN ('paid', 'unpaid')),
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- Admins table
CREATE TABLE IF NOT EXISTS admins (
    id          BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    is_super    BOOLEAN NOT NULL DEFAULT FALSE,
    added_by    BIGINT,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Payments table
-- IMPORTANT: receipt_file_id stores the Telegram file_id (NOT message_id).
-- This is needed so the admin inbox can call send_photo(photo=file_id).
-- The original bot only stored receipt_channel_msg_id (message ID ≠ file ID).
CREATE TABLE IF NOT EXISTS payments (
    id                     BIGSERIAL PRIMARY KEY,
    telegram_id            BIGINT NOT NULL REFERENCES users(telegram_id),
    month                  INT NOT NULL CHECK (month BETWEEN 1 AND 13),
    year                   INT NOT NULL CHECK (year > 1900),
    receipt_channel_msg_id BIGINT,
    receipt_file_id        TEXT,           -- Telegram file_id for photo display
    status                 TEXT NOT NULL DEFAULT 'pending'
                           CHECK (status IN ('pending', 'approved', 'rejected')),
    rejected_reason        TEXT,
    eth_payment_date       TEXT,           -- Storage format: "YYYY-MM-DD"
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_payments_telegram_id ON payments(telegram_id);
CREATE INDEX IF NOT EXISTS idx_payments_status      ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_month_year  ON payments(month, year);

-- Settings key/value store
-- Stores: billing days, message templates, notification toggles,
--         and Phase 7 last-run dates for missed-job recovery.
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Bank accounts
CREATE TABLE IF NOT EXISTS bank_accounts (
    id              BIGSERIAL PRIMARY KEY,
    bank_name       TEXT NOT NULL,
    account_number  TEXT NOT NULL,
    account_holder  TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Support messages
CREATE TABLE IF NOT EXISTS support_messages (
    id          BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    message     TEXT NOT NULL,
    reply       TEXT,
    replied_by  BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    replied_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_support_unanswered ON support_messages(reply) WHERE reply IS NULL;

-- ============================================================
-- Seed default settings (safe to run multiple times — uses ON CONFLICT DO NOTHING)
-- ============================================================

INSERT INTO settings (key, value) VALUES
    ('billing_start_day',    '25'),
    ('billing_end_day',      '5'),
    ('msg_payment_start',    '📢 ውድ አባላት,\n\nየዚህ ወር የደንበኝነት ክፍያ ጊዜ ደርሷል! ከ{start_day}ኛ እስከ {end_day}ኛ ባለው ጊዜ ውስጥ ክፍያዎን እንዲፈጽሙ ጥሪ እናቀርባለን።\n\n💳 ለክፍያ መመሪያ ዋናውን ምናሌ ይጠቀሙ።'),
    ('msg_reminder_one_day', '⚠️ ትዝታ!\n\nነገ {end_day}ኛ — የደንበኝነት ክፍያ የሚቆምበት ቀን ነው። ገና ካልከፈሉ፣ ዛሬ ክፍያዎን ፈጽሙ!\n\n💳 ''ክፈል/አድስ'' የሚለውን ምናሌ ይጠቀሙ።'),
    ('msg_final_day',        '🚨 የመጨረሻ ቀን!\n\nዛሬ {end_day}ኛ — የደንበኝነት ክፍያ የመጨረሻ ቀን ነው። ገና ካልከፈሉ ወዲያውኑ ይፈጽሙ!\n\n⏳ ዛሬ ካልፈጸሙ አገልግሎቱ ይቋረጣል።'),
    ('msg_approved',         '✅ *ክፍያዎ ተቀብሏል!*\n\nስም: {name}\nወር: {month} (ዓ.ም)\n\nአመሰግናለሁ! አባልነትዎ ታድሷል። 🎉'),
    ('msg_rejected',         '❌ *ክፍያዎ ተቀባይነት አላገኘም።*\n\nምክንያት: {reason}\n\nእባክዎ ትክክለኛ ደረሰኝ ፎቶ ልከው እንደገና ይሞክሩ።'),
    ('notify_payment_start', 'true'),
    ('notify_one_day',       'true'),
    ('notify_final_day',     'true'),
    ('last_run_payment_start', ''),
    ('last_run_one_day',       ''),
    ('last_run_final_day',     ''),
    ('last_run_monthly_reset', '')
ON CONFLICT (key) DO NOTHING;
