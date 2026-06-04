"""
texts.py
────────
SINGLE SOURCE OF TRUTH for all Amharic (and mixed) UI strings.
No Amharic strings should appear anywhere else in the codebase.
"""


class T:
    # ──────────────────────────────────────────────────────────────────────────
    #  REGISTRATION / PHONE COLLECTION
    # ──────────────────────────────────────────────────────────────────────────
    BTN_SHARE_PHONE = "📱 ስልክ ቁጥር አጋራ"

    REGISTER_WELCOME_NEW = (
        "👋 *እንኳን ደህና መጡ, {name}!*\n\n"
        "ይህ ቦት የደንበኝነት ክፍያዎን ለማስተዳደር ይረዳዎታል።\n\n"
        "📱 ለመጀመር እባክዎ ስልክ ቁጥርዎን ያጋሩ:"
    )
    REGISTER_PHONE_PROMPT = (
        "📱 *ስልክ ቁጥር ያስፈልጋል*\n\n"
        "እባክዎ ከታቹ ያለውን ቁልፍ ተጠቅሞ ስልክ ቁጥርዎን ያጋሩ:"
    )
    REGISTER_PHONE_INVALID = (
        "❌ ስልክ ቁጥር አልደረሰም።\n"
        "እባክዎ ከታቹ ያለውን ቁልፍ ተጠቅሞ ያጋሩ:"
    )
    REGISTER_SUCCESS = (
        "✅ *ምዝገባዎ ተጠናቋል!*\n\n"
    )

    # ──────────────────────────────────────────────────────────────────────────
    #  BOT COMMANDS
    # ──────────────────────────────────────────────────────────────────────────
    CMD_START_DESC  = "ቦቱን ጀምር"
    CMD_ADMIN_DESC  = "የአስተዳዳሪ ፓነል"
    CMD_CANCEL_DESC = "ሂደቱን ሰርዝ"

    # ──────────────────────────────────────────────────────────────────────────
    #  MAIN MENU BUTTONS
    # ──────────────────────────────────────────────────────────────────────────
    BTN_MY_PROFILE = "👤 የእኔ መገለጫ"
    BTN_PAY_RENEW  = "💳 ክፈል / አድስ"
    BTN_SCHEDULE   = "📅 የክፍያ መርሃ ግብር"
    BTN_SUPPORT    = "📝 ድጋፍ እና ታሪክ"

    # ──────────────────────────────────────────────────────────────────────────
    #  WELCOME / START
    # ──────────────────────────────────────────────────────────────────────────
    WELCOME = (
        "👋 *እንኳን ደህና መጡ, {name}!*\n\n"
        "ይህ ቦት የደንበኝነት ክፍያዎን ለማስተዳደር ይረዳዎታል።\n"
        "ከታቹ ምናሌ ምርጫዎን ያድርጉ:"
    )
    UNKNOWN_COMMAND = (
        "❓ ምርጫዎን ከምናሌ ያድርጉ።\n/start ብለው ምናሌ ያሳዩ።"
    )
    OPERATION_CANCELLED = "❌ *ሂደቱ ተሰርዟል።*"

    # ──────────────────────────────────────────────────────────────────────────
    #  PROFILE
    # ──────────────────────────────────────────────────────────────────────────
    PROFILE_HEADER    = "👤 *የእኔ መገለጫ*"
    PROFILE_NAME      = "📛 ስም"
    PROFILE_PHONE_LBL = "📱 ስልክ"
    PROFILE_TG_ID     = "🆔 Telegram ID"
    PROFILE_STATUS    = "📊 ሁኔታ"
    PROFILE_JOINED    = "📅 ተቀጥሮ"
    PROFILE_ETH_SUFFIX = "(ዓ.ም)"

    STATUS_PAID   = "✅ ተከፍሏል"
    STATUS_UNPAID = "❌ አልተከፈለም"

    BTN_EDIT_NAME  = "✏️ ስም ቀይር"
    BTN_EDIT_PHONE = "📱 ስልክ ቁጥር ቀይር"

    PROFILE_TEXT = (
        "{header}\n\n"
        "{name_lbl}: *{name}*\n"
        "{phone_lbl}: {phone}\n"
        "{id_lbl}: `{tg_id}`\n"
        "{status_lbl}: *{status}*\n"
        "{joined_lbl}: {joined} {eth_suffix}"
    )

    EDIT_NAME_PROMPT    = "✏️ *ስም ቀይር*\n\nአዲሱን ስምዎን ያስገቡ:"
    EDIT_NAME_TOO_SHORT = "❌ ስሙ ከ 2 እስከ 60 ፊደላት መሆን አለበት። እንደገና ያስገቡ:"
    EDIT_NAME_SUCCESS   = "✅ ስምዎ ወደ *{name}* ተቀይሯል!"

    EDIT_PHONE_PROMPT   = (
        "📱 *ስልክ ቁጥር ቀይር*\n\n"
        "ከታቹ ያለውን ቁልፍ ተጠቅሞ አዲሱን ቁጥር ያጋሩ:"
    )
    EDIT_PHONE_SUCCESS  = "✅ ስልክ ቁጥርዎ ወደ *{phone}* ተቀይሯል!"
    EDIT_PHONE_INVALID  = (
        "❌ ስልክ ቁጥር አልደረሰም።\n"
        "እባክዎ ከታቹ ያለውን ቁልፍ ተጠቅሞ ያጋሩ:"
    )

    PROFILE_NOT_FOUND = "❌ ፕሮፋይልዎ አልተገኘም። /start ይጠቀሙ።"
    PROFILE_NO_PHONE  = "—"

    # ──────────────────────────────────────────────────────────────────────────
    #  PAYMENT FLOW
    # ──────────────────────────────────────────────────────────────────────────
    PAYMENT_ALREADY_PAID = (
        "✅ *ክፍያዎ ለዚህ ወር ጸድቋል!*\n\n"
        "ምንም ተጨማሪ ክፍያ አያስፈልግዎትም።"
    )
    PAYMENT_ALREADY_PENDING = (
        "⏳ *ደረሰኙ ቀርቧል — ክፍያዎ በጥበቃ ላይ ነው።*\n\n"
        "አስተዳዳሪዎቹ እስኪያረጋግጡ ይጠብቁ።"
    )
    PAYMENT_NO_BANK = (
        "⚠️ *የባንክ ሒሳብ አልተገኘም*\n\n"
        "እባክዎ ቆይተው እንደገና ይሞክሩ። ወይም ድጋፍ ቡድኑን ያናግሩ።"
    )
    PAYMENT_BANK_HEADER = "🏦 *የክፍያ ሒሳቦች:*\n\n"
    PAYMENT_BANK_ROW = (
        "🏦 ባንክ: *{bank_name}*\n"
        "💳 ሒሳብ ቁጥር: `{account_number}`\n"
        "👤 ተቀባይ: *{account_holder}*\n\n"
    )
    PAYMENT_BANK_FOOTER = (
        "━━━━━━━━━━━━━━━\n"
        "📸 *ክፍያ ፈጽመው ካበቁ, ደረሰኝ ፎቶ ያስቀምጡ።*\n"
        "_(ክፍያ ሳያደርጉ ለማቆም /cancel ያስገቡ)_"
    )

    PAYMENT_PHOTO_ONLY = (
        "❌ *ፎቶ ብቻ ይቀበላሉ!*\n\nደረሰኝ ፎቶዎን ያስቀምጡ:"
    )
    PAYMENT_SCREENSHOT_RECEIVED = (
        "📸 *ደረሰኝ ደርሶናል!*\n\n"
        "ደረሰኙን ወደ አስተዳዳሪ ቡድን ልኬዋለሁ ማለት ይፈልጋሉ?"
    )
    BTN_CONFIRM_PAYMENT = "✅ ልኬዋለሁ, አረጋግጥ"
    BTN_CANCEL_PAYMENT  = "❌ ሰርዝ"

    PAYMENT_CANCELLED = (
        "❌ *ክፍያ ተሰርዟል።*\n\nለማስቀጠል ዋናው ምናሌ ይጠቀሙ።"
    )
    PAYMENT_NO_CHANNEL = (
        "❌ *የደረሰኝ መቀበያ ቻናል አልተቀናበረም።*\n\nእባክዎ አስተዳዳሪን ያናግሩ።"
    )
    PAYMENT_SENDING = "⏳ ደረሰኝ ወደ አስተዳዳሪ ቡድን እየተላከ ነው..."
    PAYMENT_SEND_FAILED = (
        "❌ *ደረሰኝ ወደ ቻናሉ መላክ አልተቻለም።*\n\n"
        "እባክዎ ቆይተው ወይም ድጋፍ ቡድኑን ያናግሩ።"
    )
    PAYMENT_SUCCESS = (
        "✅ *ደረሰኝዎ ተልኳል!*\n\n"
        "አስተዳዳሪዎቹ ካረጋገጡ ሁኔታዎ ይዘምናል።\n"
        "ትንሽ ቢጠብቁ ምስጋናዬ ነው! 🙏"
    )
    PAYMENT_NO_PHOTO  = "❌ ፎቶ አልተገኘም። እንደገና ይሞክሩ።"
    BACK_TO_MENU      = "ወደ ዋናው ምናሌ ተመልሰዋል።"

    RECEIPT_CAPTION = (
        "📸 *አዲስ ደረሰኝ*\n\n"
        "👤 ተጠቃሚ: {name}\n"
        "🆔 ID: `{tg_id}`\n"
        "📅 ቀን (ዓ.ም): {eth_date}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    #  PAYMENT SCHEDULE
    # ──────────────────────────────────────────────────────────────────────────
    SCHEDULE_HEADER  = "📅 *የክፍያ መርሃ ግብር*"
    SCHEDULE_MONTH   = "📆 ወር: *{month_name} {year} (ዓ.ም)*"
    SCHEDULE_CYCLE   = "📌 የክፍያ ዑደት: *{start}ኛ — {end}ኛ*"
    SCHEDULE_USER_STATUS = "📊 የእርስዎ ሁኔታ: *{status}*"
    SCHEDULE_NEXT    = "🔔 ቀጣይ: _{event}_"
    SCHEDULE_DIVIDER = "━━━━━━━━━━━━━━━"

    SCHEDULE_DAYS_LEFT     = "⏳ {days} ቀናት ቀርተዋል"
    SCHEDULE_ONE_DAY_LEFT  = "⚠️ ነገ የመጨረሻ ቀን ነው!"
    SCHEDULE_LAST_DAY      = "🚨 ዛሬ የመጨረሻ ቀን ነው!"
    SCHEDULE_DAYS_TO_START = "⏳ ክፍያ ለመጀመር {days} ቀናት ቀርተዋል"
    SCHEDULE_NEXT_END      = "የክፍያ ጊዜ {end}ኛ ቀን ያበቃል"
    SCHEDULE_NEXT_START    = "ክፍያ {start}ኛ ቀን ይጀምራል"

    # ──────────────────────────────────────────────────────────────────────────
    #  SUPPORT & HISTORY
    # ──────────────────────────────────────────────────────────────────────────
    SUPPORT_MENU_HEADER = "📝 *ድጋፍ እና ታሪክ*\nምርጫዎን ያድርጉ:"
    BTN_PAYMENT_HISTORY = "📋 የክፍያ ታሪክ"
    BTN_CONTACT_SUPPORT = "💬 ድጋፍ ቡድን ያናግሩ"

    HISTORY_HEADER          = "📋 *የክፍያ ታሪክ:*\n"
    HISTORY_EMPTY           = "📋 *የክፍያ ታሪክ*\n\nምንም ታሪክ አልተገኘም።"
    HISTORY_APPROVED        = "✅"
    HISTORY_REJECTED        = "❌"
    HISTORY_PENDING         = "⏳"
    HISTORY_STATUS_APPROVED = "ተቀብሏል"
    HISTORY_STATUS_REJECTED = "ተቀባይነት አላገኘም"
    HISTORY_STATUS_PENDING  = "በመጠባበቅ ላይ"

    SUPPORT_PROMPT = (
        "💬 *ድጋፍ ቡድን ያናግሩ*\n\n"
        "ጥያቄዎን ወይም አስተያየትዎን ያስገቡ:\n"
        "_(ለማቆም /cancel ያስገቡ)_"
    )
    SUPPORT_TOO_SHORT = "❌ መልዕክቱ በጣም አጭር ነው። ቢያንስ 5 ፊደላት ያስፈልጋሉ:"
    SUPPORT_SENT = (
        "✅ *ጥያቄዎ ተልኳል!*\n\n"
        "የድጋፍ ቡድናችን በቅርቡ ይመልሱዎታል። 🙏"
    )

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN — GENERAL
    # ──────────────────────────────────────────────────────────────────────────
    ADMIN_NOT_AUTHORIZED = "⛔ ይህን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም።"
    ADMIN_SUPER_ONLY     = "⛔ ይህ ትዕዛዝ ለዋና አስተዳዳሪ ብቻ ነው።"

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN — MAIN PANEL
    # ──────────────────────────────────────────────────────────────────────────
    ADMIN_PANEL_HEADER = (
        "🔐 *የአስተዳዳሪ ፓነል*\n\n"
        "👥 ጠቅላላ ተጠቃሚዎች: *{total}*\n"
        "✅ ይሄ ወር ከፍለዋል: *{paid}*\n\n"
        "ከታቹ ምናሌ ምርጫዎን ያድርጉ:"
    )

    BTN_ADM_MANAGE   = "🛡️ አስተዳዳሪ አስተዳደር"
    BTN_ADM_SETTINGS = "⚙️ ስርዓት ቅንብሮች"
    BTN_ADM_USERS    = "👥 ተጠቃሚ አስተዳደር"
    BTN_ADM_INBOX    = "📩 መልዕክቶች እና ደረሰኞች"
    BTN_ADM_REPORT   = "📊 የፋይናንስ ሪፖርት"
    BTN_BACK         = "◀️ ተመለስ"

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN — ADMIN MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────
    MANAGE_HEADER      = "🛡️ *አስተዳዳሪ አስተዳደር*\nምርጫዎን ያድርጉ:"
    BTN_ADD_ADMIN      = "➕ አስተዳዳሪ ጨምር"
    BTN_REMOVE_ADMIN   = "➖ አስተዳዳሪ አስወግድ"
    BTN_LIST_ADMINS    = "📋 አስተዳዳሪዎች ዝርዝር"

    ADD_ADMIN_PROMPT   = "➕ *አስተዳዳሪ ጨምር*\n\nአዲሱን አስተዳዳሪ Telegram ID ያስገቡ:"
    ADD_ADMIN_INVALID  = "❌ ትክክለኛ ID ያስገቡ (ቁጥር ብቻ):"
    ADD_ADMIN_SUCCESS  = "✅ ID `{tg_id}` አስተዳዳሪ ሆኗል።"

    REMOVE_ADMIN_HEADER    = "➖ *አስተዳዳሪ አስወግድ*\nማስወገድ የሚፈልጉትን ይምረጡ:"
    REMOVE_ADMIN_NONE      = "❌ ምንም አስተዳዳሪ አልተገኘም።"
    REMOVE_ADMIN_SUCCESS   = "✅ ID `{tg_id}` አስተዳዳሪነት ተወግዷል።"
    REMOVE_ADMIN_SUPER_ERROR = "❌ ዋና አስተዳዳሪን ማስወገድ አይቻልም።"

    LIST_ADMINS_HEADER = "📋 *አስተዳዳሪዎች ዝርዝር:*\n"
    LIST_ADMINS_EMPTY  = "📋 አሁን ያሉ አስተዳዳሪዎች የሉም።"
    ADMIN_ROLE_SUPER   = "⭐ ዋና"
    ADMIN_ROLE_REGULAR = "🔑 ሁለተኛ"

    MANAGE_SUPER_ONLY = "⛔ ለዋና አስተዳዳሪ ብቻ ነው።"

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN — SETTINGS
    # ──────────────────────────────────────────────────────────────────────────
    SETTINGS_HEADER   = "⚙️ *ስርዓት ቅንብሮች*\nምርጫዎን ያድርጉ:"
    BTN_EDIT_MESSAGES = "✏️ መልዕክቶችን አርትዕ"
    BTN_NOTIFY_TOGGLE = "🔔 ማሳወቂያ ቅንብር"
    BTN_BILLING_CYCLE = "📅 የክፍያ ዑደት"
    BTN_BANK_ACCOUNTS = "🏦 የባንክ ሒሳብ"

    EDIT_MSG_HEADER = "✏️ *መልዕክቶችን አርትዕ*\nየትኛውን ማርትዕ ይፈልጋሉ?"
    EDIT_MSG_PROMPT = (
        "✏️ *{label}*\n\n"
        "አሁን ያለው:\n```{current}```\n\n"
        "አዲሱን ጽሑፍ ይላኩ (ለሰርዝ /cancel ይጠቀሙ):"
    )
    EDIT_MSG_SUCCESS = "✅ *{label}* ዘምኗል!"
    EDIT_MSG_TIMEOUT = "❌ ሂደቱ ጊዜ አልፎታል። እንደገና ይሞክሩ።"

    NOTIFY_HEADER = "🔔 *ማሳወቂያ ቅንብሮች*\nለማብራት/ለማጥፋት ይምረጡ:"
    NOTIFY_ON     = "🟢 ነቅቷል"
    NOTIFY_OFF    = "🔴 ጠፍቷል"

    BILLING_CYCLE_HEADER = (
        "📅 *የክፍያ ዑደት*\n\n"
        "የጅምር ቀን: **{start}ኛ**\n"
        "የማብቂያ ቀን: **{end}ኛ**"
    )
    BTN_EDIT_START_DAY   = "✏️ የጅምር ቀን ቀይር"
    BTN_EDIT_END_DAY     = "✏️ የማብቂያ ቀን ቀይር"
    BILLING_START_PROMPT = "📅 አዲሱን የጅምር ቀን ቁጥር ያስገቡ (ለምሳሌ: 25):"
    BILLING_END_PROMPT   = "📅 አዲሱን የማብቂያ ቀን ቁጥር ያስገቡ (ለምሳሌ: 5):"
    BILLING_INVALID      = "❌ ትክክለኛ ቀን (1–30) ያስገቡ:"
    BILLING_START_SAVED  = "✅ የጅምር ቀን ወደ **{day}ኛ** ተቀይሯል።"
    BILLING_END_SAVED    = "✅ የማብቂያ ቀን ወደ **{day}ኛ** ተቀይሯል።"

    BANK_HEADER      = "🏦 *የባንክ ሒሳቦች*\n\n"
    BANK_NONE        = "ምንም ሒሳብ አልተጨመረም።\n\n"
    BANK_ROW         = "🏦 {bank_name}\n💳 {account_number}\n👤 {account_holder}\n\n"
    BTN_ADD_BANK     = "➕ ሒሳብ ጨምር"
    BANK_NAME_PROMPT = "🏦 የባንኩን ስም ያስገቡ (ለምሳሌ: ቢሮ፣ ዳሸን ወዘተ):"
    BANK_ACCT_PROMPT = "💳 የሒሳብ ቁጥሩን ያስገቡ:"
    BANK_HOLDER_PROMPT = "👤 የሒሳብ ባለቤቱን ሙሉ ስም ያስገቡ:"
    BANK_ADDED       = "✅ ሒሳብ ተጨምሯል!\n🏦 {bank_name}\n💳 {acct}\n👤 {holder}"

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN — USER MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────
    USERS_MENU_HEADER = "👥 *ተጠቃሚ አስተዳደር*:"
    BTN_ALL_USERS    = "📋 ሁሉም ተጠቃሚዎች"
    BTN_DEBTORS      = "❌ ያልከፈሉ (ዕዳ ያለባቸው)"
    BTN_MANUAL_EDIT  = "✏️ ተጠቃሚ ማስተካከያ"

    USERS_ALL_HEADER = "👥 *ሁሉም ተጠቃሚዎች ({count}):*\n"
    USERS_ALL_EMPTY  = "👥 ምንም ተጠቃሚ አልተገኘም።"
    USERS_ALL_MORE   = "\n...እና {n} ተጨማሪ ተጠቃሚዎች"

    DEBTORS_HEADER = "❌ *ያልከፈሉ ተጠቃሚዎች ({count}):*\n"
    DEBTORS_NONE   = "🎉 ሁሉም ተጠቃሚዎች ከፍለዋል!"

    MANUAL_PROMPT_ID   = "✏️ *ተጠቃሚ ማስተካከያ*\n\nየተጠቃሚው Telegram ID ያስገቡ:"
    MANUAL_INVALID_ID  = "❌ ትክክለኛ ID ያስገቡ:"
    MANUAL_NOT_FOUND   = "❌ ይህ ተጠቃሚ አልተገኘም። ID እንደገና ያረጋግጡ:"
    MANUAL_USER_INFO   = (
        "👤 *ተጠቃሚ:* {name}\n"
        "🆔 ID: `{tg_id}`\n"
        "📊 ሁኔታ: {icon} {status}\n\n"
        "ምን ማድረግ ይፈልጋሉ?"
    )
    BTN_MARK_PAID        = "✅ ተከፍሏል ምልክት"
    BTN_MARK_UNPAID      = "❌ አልተከፈለም ምልክት"
    BTN_RENAME_USER      = "✏️ ስም ቀይር"
    MANUAL_MARKED_PAID   = "✅ ID `{tg_id}` ተከፍሏል ተብሎ ተመዝግቧል።"
    MANUAL_MARKED_UNPAID = "❌ ID `{tg_id}` አልተከፈለም ተብሎ ተለውጧል።"
    MANUAL_RENAME_PROMPT  = "✏️ አዲሱን ስም ያስገቡ:"
    MANUAL_RENAME_SUCCESS = "✅ ስም ወደ *{name}* ተቀይሯል።"

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN — INBOX
    # ──────────────────────────────────────────────────────────────────────────
    INBOX_HEADER         = "📩 *መልዕክቶች እና ደረሰኞች*\nምርጫዎን ያድርጉ:"
    BTN_PENDING_RECEIPTS = "📸 ያልተፈቀዱ ደረሰኞች"
    BTN_SUPPORT_INBOX    = "💬 ያልተመለሱ ጥያቄዎች"
    BTN_BROADCAST        = "📣 ለሁሉም ዑደቱ"

    RECEIPTS_NONE   = "✅ *ያልተፈቀደ ደረሰኝ የለም።*\nሁሉም ዘምኗል!"
    RECEIPTS_HEADER = "📸 *ያልተፈቀዱ ደረሰኞች ({count}):*"

    RECEIPT_REVIEW_CAPTION = (
        "📸 *ደረሰኝ ለፍተሻ*\n\n"
        "👤 ስም: {name}\n"
        "🆔 ID: `{tg_id}`\n"
        "📅 ቀን: {eth_date}\n"
        "🔢 ክፍያ ID: #{payment_id}"
    )
    BTN_APPROVE = "✅ ፍቀድ"
    BTN_REJECT  = "❌ አትቀበል"

    APPROVE_SUCCESS      = "✅ *ደረሰኝ #{payment_id} ጸድቋል!*\n\nተጠቃሚው ማሳወቂያ ተልኳል።"
    REJECT_REASON_PROMPT = "❌ *ለምን አትቀበሉም?*\n\nምክንያቱን ያስገቡ:"
    REJECT_SUCCESS       = "❌ *ደረሰኝ #{payment_id} ተቀባይነት አላገኘም።*"

    NOTIFY_APPROVED = (
        "✅ *ክፍያዎ ተቀብሏል!*\n\n"
        "ስም: {name}\n"
        "ወር: {month} (ዓ.ም)\n\n"
        "አመሰግናለሁ! አባልነትዎ ታድሷል። 🎉"
    )
    NOTIFY_REJECTED = (
        "❌ *ክፍያዎ ተቀባይነት አላገኘም።*\n\n"
        "ምክንያት: {reason}\n\n"
        "እባክዎ ትክክለኛ ደረሰኝ ፎቶ ልከው እንደገና ይሞክሩ።"
    )

    SUPPORT_MSGS_NONE   = "✅ *ያልተመለሱ ጥያቄዎች የሉም።*"
    SUPPORT_MSGS_HEADER = "💬 *ያልተመለሱ ጥያቄዎች ({count}):*\n\n"
    SUPPORT_MSG_ITEM    = "#{msg_id} — {name} (`{tg_id}`):\n_{message}_\n"
    BTN_REPLY_MSG       = "💬 #{msg_id} ምላሽ ስጥ"
    SUPPORT_REPLY_PROMPT  = "💬 *ምላሽ ለ #{msg_id}*\n\nጥያቄ: _{message}_\n\nምላሽዎን ያስገቡ:"
    SUPPORT_REPLY_SUCCESS = "✅ ምላሽ ተልኳል!"
    SUPPORT_REPLY_TO_USER = (
        "💬 *ከድጋፍ ቡድናችን ምላሽ:*\n\n"
        "_{reply}_\n\n"
        "— ድጋፍ ቡድን"
    )

    BROADCAST_PROMPT = (
        "📣 *ለሁሉም ዑደቱ*\n\n"
        "ለሁሉም ተጠቃሚዎች ለመላክ ጽሑፍ ወይም ፎቶ ይላኩ:\n"
        "_(ለመሰረዝ /cancel ያስገቡ)_"
    )
    BROADCAST_SENDING = "⏳ ወደ {count} ተጠቃሚዎች እየተላከ ነው..."
    BROADCAST_DONE    = "✅ *ዑደቱ ተጠናቅቋል!*\n\n📨 ተልኳል: *{sent}*\n❌ አልተላከም: *{failed}*"

    # ──────────────────────────────────────────────────────────────────────────
    #  ADMIN — REPORTS
    # ──────────────────────────────────────────────────────────────────────────
    REPORT_MENU_HEADER = "📊 *የፋይናንስ ሪፖርት*\nምርጫዎን ያድርጉ:"
    BTN_QUICK_REPORT   = "📊 ፈጣን ሪፖርት"
    BTN_PAYMENT_EXCEL  = "📥 የክፍያ ዝርዝር (Excel)"
    BTN_ATTEND_EXCEL   = "📋 የተሳታፊነት ሪፖርት (Excel)"
    BTN_NOTIFY_UNPAID  = "📣 ያልከፈሉ ማሳወቅ"

    REPORT_PICK_MONTH = "📊 *{title} — ወር ይምረጡ:*"

    QUICK_REPORT_TEXT = (
        "📊 *ፈጣን ሪፖርት — {month_name} {year} (ዓ.ም)*\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "👥 ጠቅላላ ተጠቃሚዎች: *{total}*\n"
        "✅ ከፍለዋል: *{paid}*\n"
        "❌ አልከፈሉም: *{unpaid}*\n"
        "⏳ በጥበቃ ላይ: *{pending}*\n"
        "🚫 ተቀባይነት አላገኘም: *{rejected}*\n\n"
        "📈 የክፍያ መጠን: *{pct}%*\n"
        "`[{bar}]`"
    )

    EXCEL_GENERATING   = "⏳ Excel ፋይል እየተዘጋጀ ነው..."
    EXCEL_PAYMENT_FNAME = "payments_{month}_{year}.xlsx"
    EXCEL_ATTEND_FNAME  = "attendance_{month}_{year}.xlsx"
    EXCEL_CAPTION      = "📥 {fname}"
    EXCEL_ERROR        = "❌ ፋይሉን ማዘጋጀት አልተቻለም። እንደገና ይሞክሩ።"

    NOTIFY_PICK_MONTH = "📣 *ያሳወቅ — ወር ይምረጡ:*\n\nለምን ወር ያልከፈሉ ተጠቃሚዎች ማሳወቅ ይፈልጋሉ?"
    NOTIFY_ALL_PAID   = "✅ *{month_name} {year} (ዓ.ም)*\n\nሁሉም ተጠቃሚዎች ለዚህ ወር ከፍለዋል! ምንም ማሳወቂያ አያስፈልግም።"
    NOTIFY_PREVIEW    = (
        "📣 *{month_name} {year} (ዓ.ም) — ያሳወቅ ቅድሚያ ዕይታ*\n\n"
        "❌ *{count} ተጠቃሚዎች* ለዚህ ወር ገና አልከፈሉም:\n\n"
        "{preview}\n\n"
        "ማሳወቂያ ወደ ሁሉም ልካቸው?"
    )
    BTN_CONFIRM_NOTIFY = "📨 አዎ — {count} ሰዎች ላክ"
    BTN_CANCEL_NOTIFY  = "❌ ሰርዝ"
    NOTIFY_SENDING     = "⏳ ማሳወቂያ ወደ {count} ተጠቃሚዎች እየተላከ ነው..."
    NOTIFY_DONE        = (
        "✅ *ማሳወቂያ ተልኳል!*\n\n"
        "📅 ወር: *{month_name} {year} (ዓ.ም)*\n"
        "📨 ተልኳል:   *{sent}*\n"
        "❌ አልተላከም: *{failed}*"
    )
    NOTIFY_NONE_UNPAID  = "✅ ሁሉም ተከፍሏል — ምንም ለማሳወቅ የለም።"
    BTN_BACK_TO_REPORT  = "◀️ ወደ ሪፖርት ተመለስ"

    # ──────────────────────────────────────────────────────────────────────────
    #  AUTOMATED REMINDERS
    # ──────────────────────────────────────────────────────────────────────────
    DEFAULT_MSG_PAYMENT_START = (
        "📢 ውድ አባላት,\n\n"
        "የዚህ ወር የደንበኝነት ክፍያ ጊዜ ደርሷል! "
        "ከ{start_day} እስከ {end_day} ባለው ጊዜ ውስጥ ክፍያዎን እንዲፈጽሙ ጥሪ እናቀርባለን።\n\n"
        "💳 ለክፍያ መመሪያ ዋናውን ምናሌ ይጠቀሙ።"
    )
    DEFAULT_MSG_ONE_DAY = (
        "⚠️ ትዝታ!\n\n"
        "ነገ {end_day} የሚከፈለው የደንበኝነት ቀን ነው። "
        "ገና ካልከፈሉ፣ ዛሬ ክፍያዎን ፈጽሙ!\n\n"
        "💳 'ክፈል/አድስ' የሚለውን ምናሌ ይጠቀሙ።"
    )
    DEFAULT_MSG_FINAL_DAY = (
        "🚨 የመጨረሻ ቀን!\n\n"
        "ዛሬ {end_day} — የደንበኝነት ክፍያ የመጨረሻ ቀን ነው። "
        "ገና ካልከፈሉ ወዲያውኑ ይፈጽሙ!\n\n"
        "⏳ ዛሬ ካፈሱ አገልግሎቱ ይቋረጣል።"
    )

    # ──────────────────────────────────────────────────────────────────────────
    #  MONTHLY CYCLE RESET REPORT
    # ──────────────────────────────────────────────────────────────────────────
    CYCLE_RESET_REPORT = (
        "📊 *የወር ዑደት ሪፖርት — {month_name} {year} (ዓ.ም)*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👥 ጠቅላላ ተጠቃሚዎች:   *{total}*\n"
        "✅ ክፍያ ፈጽመዋል:      *{paid}*\n"
        "❌ አልከፈሉም:          *{unpaid}*\n"
        "⏳ በጥበቃ ላይ:         *{pending}*\n"
        "🚫 ተቀባይነት አላገኘም:  *{rejected}*\n\n"
        "📈 የክፍያ መጠን: *{pct}%*\n"
        "`[{bar}]`\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "❌ *ያልከፈሉ ተጠቃሚዎች:*\n"
        "{unpaid_list}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔄 *ሁሉም ተጠቃሚዎች ለአዲሱ ዑደት 'አልተከፈለም' ሆነዋል።*\n"
        "🕐 ዳግም ማስጀመሪያ ቀን: {reset_datetime} (ዓ.ም)"
    )
    CYCLE_UNPAID_ALL_PAID = "  _ሁሉም ተጠቃሚዎች ከፍለዋል!_ 🎉"
    CYCLE_UNPAID_MORE     = "\n  _...እና {n} ተጨማሪ ሰዎች_"


# ── Editable message labels ────────────────────────────────────────────────────
EDITABLE_MESSAGES = {
    "msg_payment_start":    "📢 የክፍያ ጊዜ ጅምር መልዕክት",
    "msg_reminder_one_day": "⏰ አንድ ቀን ቀረ ትዝታ",
    "msg_final_day":        "🚨 የመጨረሻ ቀን መልዕክት",
    "msg_approved":         "✅ ክፍያ ጸድቋል መልዕክት",
    "msg_rejected":         "❌ ክፍያ ተቀባይነት አላገኘም መልዕክት",
}

# ── Notification toggle labels ─────────────────────────────────────────────────
NOTIFICATION_KEYS = {
    "notify_payment_start": "📢 የክፍያ ጊዜ ጅምር ማሳወቂያ",
    "notify_one_day":       "⏰ አንድ ቀን ቀረ ማሳወቂያ",
    "notify_final_day":     "🚨 የመጨረሻ ቀን ማሳወቂያ",
}
