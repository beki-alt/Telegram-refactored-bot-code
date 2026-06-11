# Telegram Payment Bot — User Guide

> A subscription payment bot with Ethiopian calendar support.
> This guide covers everything for both regular members and admins.

---

## Table of Contents

- [For Members (Regular Users)](#for-members-regular-users)
  - [Getting Started](#getting-started)
  - [Main Menu](#main-menu)
  - [How to Pay](#how-to-pay)
  - [My Profile](#my-profile)
  - [Payment History](#payment-history)
  - [Support / Contact Us](#support--contact-us)
  - [Notifications You Will Receive](#notifications-you-will-receive)
- [For Admins](#for-admins)
  - [Opening the Admin Panel](#opening-the-admin-panel)
  - [Admin Panel Overview](#admin-panel-overview)
  - [Inbox — Receipts & Messages](#inbox--receipts--messages)
  - [Reports](#reports)
  - [User Management](#user-management)
  - [Settings](#settings)
  - [Automated Reminders](#automated-reminders)
- [Commands Reference](#commands-reference)

---

## For Members (Regular Users)

### Getting Started

1. Open the bot in Telegram and send `/start`.
2. If you are new, the bot will ask for your **phone number**.
   - Tap the **"Share Contact"** button that appears, OR type your number manually (e.g. `+251912345678`).
3. Once registered, the main menu appears and you are ready to use the bot.

If you come back later and send `/start` again, it will simply show your main menu — no need to register again.

---

### Main Menu

After starting the bot you will see four buttons:

| Button | What it does |
|---|---|
| 💳 ክፈል / አድስ | Submit your payment receipt for the current month |
| 👤 መገለጫዬ | View your profile and payment status |
| 📋 ታሪክ / ድጋፍ | View payment history or send a support message |
| ℹ️ መረጃ | General information about the service |

---

### How to Pay

1. Tap **💳 ክፈል / አድስ** from the main menu.
2. The bot will show you the bank account(s) to transfer to.
3. Transfer the required amount and take a **screenshot** of the receipt.
4. Send the screenshot photo to the bot.
5. Tap **✅ አዎ — ላክ** to confirm, or **❌ ሰርዝ** to cancel.
6. You will see a success message. Your receipt goes to the admin for review.

**What happens next:**
- Your status becomes **"በጥበቃ ላይ" (Pending)** while the admin reviews.
- If approved → you receive a confirmation message and your status becomes **"ከፍሏል"**.
- If rejected → you receive a message with the reason, and you can try again.

> **Note:** You cannot submit a second payment for the same month if one is already pending or approved.
> Use `/cancel` at any time to exit the payment flow.

---

### My Profile

Tap **👤 መገለጫዬ** to see your profile card, which shows:
- Your name
- Your phone number
- Your Telegram ID
- Current payment status (✅ paid / ❌ unpaid)
- Billing window (start day → end day, Ethiopian calendar)
- Date you joined

**Editing your profile:**
Inside the profile card, tap:
- **✏️ ስም ቀይር** — change your display name (2–60 characters)
- **📞 ስልክ ቀይር** — update your phone number (share contact or type)
- **🔄 አድስ** — refresh the card to see the latest status

---

### Payment History

1. Tap **📋 ታሪክ / ድጋፍ** from the main menu.
2. Tap **📋 የክፍያ ታሪክ**.
3. Your last 10 payment records are shown with status icons:
   - ✅ Approved
   - ⏳ Pending (waiting for admin review)
   - ❌ Rejected

---

### Support / Contact Us

1. Tap **📋 ታሪክ / ድጋፍ** from the main menu.
2. Tap **💬 ድጋፍ / ጥያቄ**.
3. Type your message (at least 5 characters) and send it.
4. An admin will reply directly to you in this same chat.

---

### Notifications You Will Receive

The bot sends you automatic messages at key moments. You do not need to do anything to receive them.

| When | Message |
|---|---|
| Billing window opens | Reminder that this month's payment period has started, with the start and end dates |
| One day before the deadline | Warning that the deadline is tomorrow |
| On the deadline day | Final reminder that today is the last day to pay |
| Your receipt is approved | Confirmation that your payment was accepted |
| Your receipt is rejected | Notification with the reason, so you can resubmit |
| Admin sends a broadcast | Any general announcement from the admin |
| Admin replies to your support message | The reply comes directly to your chat |

---

---

## For Admins

### Opening the Admin Panel

Send the command `/admin` in your chat with the bot.

> Only accounts that have been added as admins (or the super-admin set via `ADMIN_ID` in the server config) can open this panel. Anyone else will be silently ignored.

---

### Admin Panel Overview

The panel header shows a live count of total members and how many have paid this month.
Four sections are accessible from the main panel:

| Section | Icon | Purpose |
|---|---|---|
| Inbox | 📩 | Review receipts, reply to support messages, broadcast |
| Reports | 📊 | Financial reports, Excel exports, notify unpaid users |
| Users | 👥 | View all members, see debtors, manually edit a user |
| Settings | ⚙️ | Billing dates, notification toggles, custom messages, bank accounts, admins |

Use `/cancel` at any time to exit a conversation mid-flow (e.g. while typing a rejection reason).

---

### Inbox — Receipts & Messages

Open with **📩 ሰሌዳ / ኢንቦክስ** → **📩 Inbox**.

#### Reviewing Receipts

1. Tap **📸 ያልተፈቀዱ ደረሰኞች** to see all pending receipts.
2. Each receipt shows: member name, Telegram ID, submission date, and the photo.
3. For each one, tap:
   - **✅ ፍቀድ** — approve. The member is instantly notified.
   - **❌ አትቀበል** — reject. You will be asked to type a reason. The member receives the reason.

#### Replying to Support Messages

1. Tap **💬 ያልተመለሱ ጥያቄዎች** to see unanswered messages (up to 10 at a time).
2. Each message shows the sender's name, ID, and message text.
3. Tap **💬 ምላሽ ስጥ** under any message.
4. Type your reply and send it. The member receives it instantly in their chat.

#### Broadcasting to All Members

1. Tap **📣 ለሁሉም ዑደቱ**.
2. Send a text message **or a photo with a caption**.
3. The bot sends it to every registered member (rate-limited to stay within Telegram limits).
4. A summary shows how many were sent and how many failed.

---

### Reports

Open with **📊 ሪፖርት**.

#### Quick Report

Tap **📊 ፈጣን ሪፖርት** to see the current month's summary:
- Total members
- Paid / Unpaid / Pending / Rejected counts
- Payment rate percentage with a visual bar

#### Excel Export

- **📥 የክፍያ ዝርዝር (Excel)** — pick a month; downloads a spreadsheet of all payment records for that month (name, ID, status, date, rejection reason).
- **📋 የተሳታፊነት ሪፖርት (Excel)** — pick a month; downloads an attendance-style report.

#### Notify Unpaid Members

1. Tap **📣 ያልከፈሉ ማሳወቅ**.
2. Pick the month you want to notify for.
3. The bot shows a preview list of unpaid members and asks for confirmation.
4. Tap **📨 አዎ — N ሰዎች ላክ** to send the reminder. Each unpaid member receives the "final day" reminder message.
5. A summary shows sent / failed counts.

> This uses the current `msg_final_day` template (customizable in Settings).

---

### User Management

Open with **👥 ተጠቃሚዎች**.

| Option | What it does |
|---|---|
| 📋 ሁሉም ተጠቃሚዎች | List all registered members (up to 50 shown) |
| ❌ ያልከፈሉ (ዕዳ ያለባቸው) | List members with unpaid status |
| ✏️ ተጠቃሚ ማስተካከያ | Manually edit a specific user by their Telegram ID |

**Manual user edit:**
1. Tap **✏️ ተጠቃሚ ማስተካከያ** and enter the user's Telegram ID.
2. The user card appears. You can:
   - **✅ ተከፍሏል ምልክት** — mark as paid
   - **❌ አልተከፈለም ምልክት** — mark as unpaid
   - **✏️ ስም ቀይር** — rename the user

---

### Settings

Open with **⚙️ ቅንብሮች**.

#### Billing Cycle Dates

These control when the payment window opens and closes each month (Ethiopian calendar days).

- Tap **⚙️ ቅንብሮች** → **📅 የክፍያ ጊዜ ቅንብር**.
- **Start day** — the day of the month the payment window opens (1–30). Tap the day on the picker keyboard, then tap ✅.
- **End day** — the day of the month the payment window closes (1–30). Same picker.

> Cross-month windows work automatically. Example: start = 25, end = 5 means the window opens on the 25th and closes on the 5th of the **next** month.

When you set the start day, the bot asks if you want to **send the payment-start notification immediately** (useful if you are setting up a cycle that starts today or tomorrow).

#### Notification Toggles

Three automated daily reminders can each be turned on or off:

| Setting | Default | When it fires |
|---|---|---|
| 🔔 የክፍያ ጊዜ ጅምር | On | On the billing start day |
| ⏰ አንድ ቀን ቀረ | On | The day before the billing end day |
| 🚨 የመጨረሻ ቀን | On | On the billing end day |

Tap the toggle button to flip On ↔ Off.

#### Custom Messages

You can edit the text of five notification messages to match your organization's style:

| Key | When it is sent |
|---|---|
| 📢 የክፍያ ጊዜ ጅምር | Billing window opens |
| ⏰ አንድ ቀን ቀረ ትዝታ | One day before deadline |
| 🚨 የመጨረሻ ቀን | On the deadline |
| ✅ ክፍያ ጸድቋል | Payment approved |
| ❌ ክፍያ ተቀባይነት አላገኘም | Payment rejected |

**To edit a message:**
1. Go to Settings → **✏️ መልዕክቶች አርትዕ** → pick the message.
2. The current text is shown. Type the new version and send it.
3. Tap ✅ to save or ❌ to keep the current text.

**Available placeholders per message type:**

| Message | Placeholders you can use |
|---|---|
| Payment start | `{month_name}` `{start_day}` `{end_day}` `{end_month_name}` |
| One day / Final day | `{end_day}` `{end_month_name}` |
| Approved | `{name}` `{month}` |
| Rejected | `{reason}` |

#### Bank Accounts

Manage the bank accounts shown to members during payment.

- **➕ ባንክ ጨምር** — add a new account (bank name, account number, account holder name).
- **📋 ባንኮች** — list active accounts with a **🗑 ሰርዝ** button next to each.

#### Admin Management

> Only the super-admin can add or remove other admins.

- **➕ አስተዳዳሪ ጨምር** — enter a Telegram ID to grant admin access.
- **📋 አስተዳዳሪዎች** — list all admins with a **❌ አስወግድ** button next to each (super-admin cannot be removed).

---

### Automated Reminders

These run on their own every day — no manual action needed.

| Job | Fires when | Audience |
|---|---|---|
| Payment start notification | Today's Ethiopian day = billing start day | All members |
| One-day warning | Today = billing end day − 1 | Unpaid members only |
| Final day notification | Today = billing end day | Unpaid members only |
| Monthly cycle reset | New month starts after a completed cycle | All admins get a summary report |

**What the monthly reset does:**
- Resets every member's status back to "unpaid" for the new cycle.
- Sends a full summary report to all admins: total members, paid/unpaid/pending/rejected counts, list of who didn't pay, and the reset timestamp.

> Members with status **"pending"** (submitted a receipt but not yet reviewed) do NOT receive the one-day or final-day reminders — they have already submitted something.

---

## Commands Reference

| Command | Who | What it does |
|---|---|---|
| `/start` | Everyone | Open the bot / register as a new member |
| `/admin` | Admins only | Open the admin panel |
| `/cancel` | Everyone | Exit any active flow (payment, support message, admin conversation) |
