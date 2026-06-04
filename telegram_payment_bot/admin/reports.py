"""
admin/reports.py
─────────────────
Reports — quick summary, Excel exports, notify-unpaid workflow.
"""

import io
import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from keyboards.admin_keyboards import month_picker_keyboard, report_menu_keyboard
from texts import T
from utils import eth_month_name, now_eth, to_ethiopian

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import openpyxl  # noqa: F401 — ensures openpyxl engine is available
    _EXCEL_AVAILABLE = True
except ImportError:
    _EXCEL_AVAILABLE = False
    logger.warning("pandas / openpyxl not installed — Excel reports disabled.")


async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Master handler for all report-related callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data
    bot   = query.get_bot()

    # ── Main report menu ─────────────────────────────────────────────────────
    if data == "adm_report":
        await query.edit_message_text(
            T.REPORT_MENU_HEADER,
            parse_mode="Markdown",
            reply_markup=report_menu_keyboard(),
        )
        return ConversationHandler.END

    # ── Quick report (current month) ─────────────────────────────────────────
    if data == "report_quick":
        now_dt                    = now_eth()
        eth_year, eth_month, _    = to_ethiopian(now_dt)
        summary                   = db.get_cycle_summary(eth_month, eth_year)
        total   = summary["total_users"]
        paid    = summary["total_paid"]
        unpaid  = summary["total_unpaid"]
        pending = summary["total_pending"]
        rejected= summary["total_rejected"]
        pct     = round(paid / total * 100) if total else 0
        filled  = int(pct / 5)
        bar     = "█" * filled + "░" * (20 - filled)

        await query.edit_message_text(
            T.QUICK_REPORT_TEXT.format(
                month_name = eth_month_name(eth_month),
                year       = eth_year,
                total      = total,
                paid       = paid,
                unpaid     = unpaid,
                pending    = pending,
                rejected   = rejected,
                pct        = pct,
                bar        = bar,
            ),
            parse_mode = "Markdown",
        )
        return ConversationHandler.END

    # ── Month pickers ────────────────────────────────────────────────────────
    if data == "report_excel_pick":
        await query.edit_message_text(
            T.REPORT_PICK_MONTH.format(title="📥 Excel ሪፖርት"),
            parse_mode="Markdown",
            reply_markup=month_picker_keyboard("report_excel"),
        )
        return ConversationHandler.END

    if data == "report_attend_pick":
        await query.edit_message_text(
            T.REPORT_PICK_MONTH.format(title="📋 ተሳታፊነት"),
            parse_mode="Markdown",
            reply_markup=month_picker_keyboard("report_attend"),
        )
        return ConversationHandler.END

    if data == "report_notify_pick":
        await query.edit_message_text(
            T.NOTIFY_PICK_MONTH,
            parse_mode="Markdown",
            reply_markup=month_picker_keyboard("report_nfy"),
        )
        return ConversationHandler.END

    # ── Excel payment report ─────────────────────────────────────────────────
    if data.startswith("report_excel_") and not data == "report_excel_pick":
        parts = data.split("_")  # report_excel_<year>_<month>
        if len(parts) < 4:
            return ConversationHandler.END
        try:
            yr, mo = int(parts[2]), int(parts[3])
        except (ValueError, IndexError):
            return ConversationHandler.END

        await query.edit_message_text(T.EXCEL_GENERATING, parse_mode="Markdown")

        if not _EXCEL_AVAILABLE:
            await bot.send_message(query.message.chat_id, T.EXCEL_ERROR)
            return ConversationHandler.END

        try:
            payments = db.get_monthly_payments(mo, yr)
            rows = []
            for i, p in enumerate(payments, 1):
                user = db.get_user(p["telegram_id"])
                rows.append({
                    "ተ.ቁ":        i,
                    "ስም":          user["name"] if user else str(p["telegram_id"]),
                    "Telegram ID": p["telegram_id"],
                    "ሁኔታ":        p["status"],
                    "የክፍያ ቀን":   str(p.get("eth_payment_date", ""))[:16],
                })
            df    = pd.DataFrame(rows)
            fname = T.EXCEL_PAYMENT_FNAME.format(month=mo, year=yr)
            buf   = io.BytesIO()
            df.to_excel(buf, index=False)
            buf.seek(0)
            await bot.send_document(
                chat_id  = query.message.chat_id,
                document = buf,
                filename = fname,
                caption  = T.EXCEL_CAPTION.format(fname=fname),
            )
        except Exception:
            logger.error(traceback.format_exc())
            await bot.send_message(query.message.chat_id, T.EXCEL_ERROR)
        return ConversationHandler.END

    # ── Excel attendance report ───────────────────────────────────────────────
    if data.startswith("report_attend_") and not data == "report_attend_pick":
        parts = data.split("_")  # report_attend_<year>_<month>
        if len(parts) < 4:
            return ConversationHandler.END
        try:
            yr, mo = int(parts[2]), int(parts[3])
        except (ValueError, IndexError):
            return ConversationHandler.END

        await query.edit_message_text(T.EXCEL_GENERATING, parse_mode="Markdown")

        if not _EXCEL_AVAILABLE:
            await bot.send_message(query.message.chat_id, T.EXCEL_ERROR)
            return ConversationHandler.END

        try:
            rows  = db.get_attendance_data(mo, yr)
            df    = pd.DataFrame(rows)
            fname = T.EXCEL_ATTEND_FNAME.format(month=mo, year=yr)
            buf   = io.BytesIO()
            df.to_excel(buf, index=False)
            buf.seek(0)
            await bot.send_document(
                chat_id  = query.message.chat_id,
                document = buf,
                filename = fname,
                caption  = T.EXCEL_CAPTION.format(fname=fname),
            )
        except Exception:
            logger.error(traceback.format_exc())
            await bot.send_message(query.message.chat_id, T.EXCEL_ERROR)
        return ConversationHandler.END

    # ── Notify unpaid — preview ───────────────────────────────────────────────
    if data.startswith("report_nfy_") and not data.startswith("report_nfyok_"):
        parts = data.split("_")  # report_nfy_<year>_<month>
        if len(parts) < 4:
            return ConversationHandler.END
        try:
            yr, mo = int(parts[2]), int(parts[3])
        except (ValueError, IndexError):
            return ConversationHandler.END

        unpaid_users = db.get_unpaid_users_for_month(mo, yr)
        month_name   = eth_month_name(mo)

        if not unpaid_users:
            await query.edit_message_text(
                T.NOTIFY_ALL_PAID.format(month_name=month_name, year=yr),
                parse_mode="Markdown",
            )
            return ConversationHandler.END

        preview_lines = [
            f"• {u['name']} (`{u['telegram_id']}`)"
            for u in unpaid_users[:10]
        ]
        if len(unpaid_users) > 10:
            preview_lines.append(f"_...+{len(unpaid_users) - 10} ሌሎች_")

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        confirm_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    T.BTN_CONFIRM_NOTIFY.format(count=len(unpaid_users)),
                    callback_data=f"report_nfyok_{yr}_{mo}",
                ),
                InlineKeyboardButton(
                    T.BTN_CANCEL_NOTIFY,
                    callback_data="adm_report",
                ),
            ]
        ])
        await query.edit_message_text(
            T.NOTIFY_PREVIEW.format(
                month_name = month_name,
                year       = yr,
                count      = len(unpaid_users),
                preview    = "\n".join(preview_lines),
            ),
            parse_mode   = "Markdown",
            reply_markup = confirm_kb,
        )
        return ConversationHandler.END

    # ── Notify unpaid — execute ───────────────────────────────────────────────
    if data.startswith("report_nfyok_"):
        parts = data.split("_")  # report_nfyok_<year>_<month>
        if len(parts) < 4:
            return ConversationHandler.END
        try:
            yr, mo = int(parts[2]), int(parts[3])
        except (ValueError, IndexError):
            return ConversationHandler.END

        unpaid_users = db.get_unpaid_users_for_month(mo, yr)
        month_name   = eth_month_name(mo)

        await query.edit_message_text(
            T.NOTIFY_SENDING.format(count=len(unpaid_users)), parse_mode="Markdown"
        )

        reminder_msg = db.get_setting("msg_reminder_one_day", T.DEFAULT_MSG_ONE_DAY)
        sent = failed = 0
        for user in unpaid_users:
            try:
                await bot.send_message(
                    chat_id    = user["telegram_id"],
                    text       = reminder_msg,
                    parse_mode = "Markdown",
                )
                sent += 1
            except Exception as exc:
                logger.warning(f"Notify unpaid failed for {user['telegram_id']}: {exc}")
                failed += 1

        await bot.send_message(
            chat_id    = query.message.chat_id,
            text       = T.NOTIFY_DONE.format(
                month_name = month_name,
                year       = yr,
                sent       = sent,
                failed     = failed,
            ),
            parse_mode = "Markdown",
        )
        return ConversationHandler.END

    return ConversationHandler.END
