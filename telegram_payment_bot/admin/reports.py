"""
admin/reports.py
─────────────────
📊 Reports — quick summary, Excel exports, and targeted notifications to unpaid users.

All dates displayed in Ethiopian calendar format.
Excel files are generated with pandas + openpyxl and sent as documents.
"""

import io
import logging

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from keyboards.admin_keyboards import back_button, month_picker_keyboard, report_menu_keyboard
from texts import T
from utils import eth_month_name

logger = logging.getLogger(__name__)


async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all report-related inline callbacks."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    # ── Menu ──────────────────────────────────────────────────────────────────
    if data == "adm_report":
        await query.edit_message_text(
            T.REPORT_MENU_HEADER,
            reply_markup=report_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    # ── Quick report (current Ethiopian month) ────────────────────────────────
    if data == "report_quick":
        from utils import now_eth, to_ethiopian
        now     = now_eth()
        eth_year, eth_month, _ = to_ethiopian(now)
        summary = db.get_cycle_summary(eth_month, eth_year)
        pct     = (
            round(summary["total_paid"] / summary["total_users"] * 100)
            if summary["total_users"] > 0 else 0
        )
        filled  = round(pct / 10)
        bar     = "█" * filled + "░" * (10 - filled)

        text = T.QUICK_REPORT_TEXT.format(
            month_name = summary["month_name"],
            year       = eth_year,
            total      = summary["total_users"],
            paid       = summary["total_paid"],
            unpaid     = summary["total_unpaid"],
            pending    = summary["total_pending"],
            rejected   = summary["total_rejected"],
            pct        = pct,
            bar        = bar,
        )
        await query.edit_message_text(
            text,
            reply_markup=back_button("adm_report"),
            parse_mode="Markdown",
        )

    # ── Month picker for Excel exports ────────────────────────────────────────
    elif data == "report_excel_pick":
        await query.edit_message_text(
            T.REPORT_PICK_MONTH.format(title="የክፍያ ዝርዝር"),
            reply_markup=month_picker_keyboard("report_excel"),
            parse_mode="Markdown",
        )

    elif data == "report_attend_pick":
        await query.edit_message_text(
            T.REPORT_PICK_MONTH.format(title="የተሳታፊነት ሪፖርት"),
            reply_markup=month_picker_keyboard("report_attend"),
            parse_mode="Markdown",
        )

    # ── Generate payment Excel ─────────────────────────────────────────────────
    elif data.startswith("report_excel_") and data.count("_") == 3:
        _, _, yr_s, mo_s = data.split("_")
        await _generate_payment_excel(query, int(mo_s), int(yr_s))

    # ── Generate attendance Excel ──────────────────────────────────────────────
    elif data.startswith("report_attend_") and data.count("_") == 3:
        _, _, yr_s, mo_s = data.split("_")
        await _generate_attendance_excel(query, int(mo_s), int(yr_s))

    # ── Notify unpaid users — month picker ────────────────────────────────────
    elif data == "report_notify_pick":
        await query.edit_message_text(
            T.NOTIFY_PICK_MONTH,
            reply_markup=month_picker_keyboard("report_nfy"),
            parse_mode="Markdown",
        )

    # ── Notify unpaid users — preview ─────────────────────────────────────────
    elif data.startswith("report_nfy_") and not data.startswith("report_nfyok_"):
        parts = data.split("_")
        yr, mo = int(parts[2]), int(parts[3])
        unpaid = db.get_unpaid_users_for_month(mo, yr)
        month_label = eth_month_name(mo)

        if not unpaid:
            await query.edit_message_text(
                T.NOTIFY_ALL_PAID.format(month_name=month_label, year=yr),
                parse_mode="Markdown",
                reply_markup=back_button("adm_report"),
            )
            return

        preview_lines = [f"  • {u['name']}" for u in unpaid[:5]]
        if len(unpaid) > 5:
            preview_lines.append(f"  _...እና {len(unpaid) - 5} ተጨማሪ_")
        preview = "\n".join(preview_lines)

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                T.BTN_CONFIRM_NOTIFY.format(count=len(unpaid)),
                callback_data=f"report_nfyok_{yr}_{mo}",
            )],
            [InlineKeyboardButton(T.BTN_CANCEL_NOTIFY, callback_data="adm_report")],
        ])
        await query.edit_message_text(
            T.NOTIFY_PREVIEW.format(
                month_name = month_label,
                year       = yr,
                count      = len(unpaid),
                preview    = preview,
            ),
            reply_markup=kb,
            parse_mode="Markdown",
        )

    # ── Notify unpaid users — send messages ───────────────────────────────────
    elif data.startswith("report_nfyok_"):
        parts = data.split("_")
        yr, mo = int(parts[2]), int(parts[3])
        month_label = eth_month_name(mo)
        unpaid = db.get_unpaid_users_for_month(mo, yr)

        if not unpaid:
            await query.edit_message_text(T.NOTIFY_NONE_UNPAID)
            return

        await query.edit_message_text(T.NOTIFY_SENDING.format(count=len(unpaid)))

        cycle    = db.get_billing_cycle()
        template = db.get_setting("msg_final_day", T.DEFAULT_MSG_FINAL_DAY)
        sent = failed = 0

        for user in unpaid:
            try:
                msg = template.format(
                    name      = user["name"],
                    month     = month_label,
                    end_day   = cycle["end"],
                    start_day = cycle["start"],
                )
                await query.get_bot().send_message(
                    chat_id    = user["telegram_id"],
                    text       = f"📣 *ትዝታ — {month_label} {yr} (ዓ.ም)*\n\n{msg}",
                    parse_mode = "Markdown",
                )
                sent += 1
            except Exception as exc:
                logger.warning(f"Notify failed for user {user['telegram_id']}: {exc}")
                failed += 1

        result = T.NOTIFY_DONE.format(
            month_name = month_label,
            year       = yr,
            sent       = sent,
            failed     = failed,
        )
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=back_button("adm_report"),
        )
        logger.info(f"Unpaid notification sent: month={mo}/{yr}, sent={sent}, failed={failed}.")


# ── Excel generators ──────────────────────────────────────────────────────────

async def _generate_payment_excel(query, eth_month: int, eth_year: int) -> None:
    """Generate and send a payment Excel report for the given Ethiopian month/year."""
    try:
        import pandas as pd
        await query.edit_message_text(T.EXCEL_GENERATING)

        payments  = db.get_monthly_payments(eth_month, eth_year)
        month_name = eth_month_name(eth_month)
        rows = []
        for i, p in enumerate(payments, 1):
            user = db.get_user(p["telegram_id"])
            name = user["name"] if user else str(p["telegram_id"])
            rows.append({
                "ተ.ቁ":        i,
                "ስም":         name,
                "Telegram ID": p["telegram_id"],
                "ወር":         f"{month_name} {eth_year}",
                "ሁኔታ":       p["status"],
                "ቀን":         p.get("eth_payment_date", ""),
                "ምክንያት":     p.get("rejected_reason", ""),
            })

        df       = pd.DataFrame(rows)
        buf      = io.BytesIO()
        fname    = T.EXCEL_PAYMENT_FNAME.format(month=eth_month, year=eth_year)
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=f"{month_name} {eth_year}")
        buf.seek(0)

        await query.get_bot().send_document(
            chat_id  = query.from_user.id,
            document = buf,
            filename = fname,
            caption  = T.EXCEL_CAPTION.format(fname=fname),
        )
        await query.edit_message_text(
            T.EXCEL_CAPTION.format(fname=fname),
            reply_markup=back_button("adm_report"),
        )

    except Exception as exc:
        logger.error(f"Payment Excel generation error: {exc}")
        await query.edit_message_text(T.EXCEL_ERROR)


async def _generate_attendance_excel(query, eth_month: int, eth_year: int) -> None:
    """Generate and send an attendance Excel report for the given Ethiopian month/year."""
    try:
        import pandas as pd
        await query.edit_message_text(T.EXCEL_GENERATING)

        rows     = db.get_attendance_data(eth_month, eth_year)
        df       = pd.DataFrame(rows)
        buf      = io.BytesIO()
        fname    = T.EXCEL_ATTEND_FNAME.format(month=eth_month, year=eth_year)
        month_name = eth_month_name(eth_month)

        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=f"{month_name} {eth_year}")
        buf.seek(0)

        await query.get_bot().send_document(
            chat_id  = query.from_user.id,
            document = buf,
            filename = fname,
            caption  = T.EXCEL_CAPTION.format(fname=fname),
        )
        await query.edit_message_text(
            T.EXCEL_CAPTION.format(fname=fname),
            reply_markup=back_button("adm_report"),
        )

    except Exception as exc:
        logger.error(f"Attendance Excel generation error: {exc}")
        await query.edit_message_text(T.EXCEL_ERROR)
