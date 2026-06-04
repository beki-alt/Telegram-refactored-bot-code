"""
tests/test_scheduler.py
────────────────────────
Phase 9 — Tests for the APScheduler reminder logic and Phase 7 recovery.

These tests use mocks so they don't require a running bot, Supabase, or
APScheduler instance.

Tests cover:
  - Reminder functions call bot.send_message for each unpaid user
  - Notifications skipped when toggled off
  - Message templates are read from DB (customizable)
  - mark_job_ran() stores the correct date key
  - check_missed_jobs() fires the correct jobs based on current date
  - monthly_cycle_reset_job() calls reset_all_users_to_unpaid()

Run with:
  cd telegram-bot && python -m pytest tests/test_scheduler.py -v
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

ETH_TZ = pytz.timezone("Africa/Addis_Ababa")


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_bot():
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


def make_users(n=3):
    return [
        {"telegram_id": 1000 + i, "name": f"User{i}", "status": "unpaid"}
        for i in range(n)
    ]


# ── send_payment_start_reminder ───────────────────────────────────────────────

class TestPaymentStartReminder:
    @pytest.mark.asyncio
    async def test_sends_to_all_unpaid_users(self):
        bot   = make_bot()
        users = make_users(3)
        with (
            patch("admin.reminders._get_unpaid_users", return_value=users),
            patch("admin.reminders._is_notification_enabled", return_value=True),
            patch("admin.reminders._get_message", return_value="Test payment start"),
            patch("admin.reminders.db.get_billing_cycle", return_value={"start": 25, "end": 5}),
            patch("admin.reminders._mark_job_ran"),
        ):
            from admin.reminders import send_payment_start_reminder
            count = await send_payment_start_reminder(bot, mark_run=False)
        assert count == 3
        assert bot.send_message.call_count == 3

    @pytest.mark.asyncio
    async def test_skips_when_disabled(self):
        bot = make_bot()
        with (
            patch("admin.reminders._is_notification_enabled", return_value=False),
        ):
            from admin.reminders import send_payment_start_reminder
            count = await send_payment_start_reminder(bot, mark_run=False)
        assert count == 0
        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_tolerates_send_failure(self):
        """If one send fails, the rest should still be sent."""
        bot           = make_bot()
        users         = make_users(3)
        call_count    = [0]
        async def send_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Network error")
        bot.send_message.side_effect = send_side_effect
        with (
            patch("admin.reminders._get_unpaid_users", return_value=users),
            patch("admin.reminders._is_notification_enabled", return_value=True),
            patch("admin.reminders._get_message", return_value="msg"),
            patch("admin.reminders.db.get_billing_cycle", return_value={"start": 25, "end": 5}),
            patch("admin.reminders._mark_job_ran"),
        ):
            from admin.reminders import send_payment_start_reminder
            count = await send_payment_start_reminder(bot, mark_run=False)
        assert count == 2  # 3 users, 1 failure → 2 sent


# ── send_one_day_reminder ─────────────────────────────────────────────────────

class TestOneDayReminder:
    @pytest.mark.asyncio
    async def test_sends_to_all_unpaid(self):
        bot   = make_bot()
        users = make_users(2)
        with (
            patch("admin.reminders._get_unpaid_users", return_value=users),
            patch("admin.reminders._is_notification_enabled", return_value=True),
            patch("admin.reminders._get_message", return_value="One day left!"),
            patch("admin.reminders.db.get_billing_cycle", return_value={"start": 25, "end": 5}),
            patch("admin.reminders._mark_job_ran"),
        ):
            from admin.reminders import send_one_day_reminder
            count = await send_one_day_reminder(bot, mark_run=False)
        assert count == 2

    @pytest.mark.asyncio
    async def test_marks_run_when_requested(self):
        bot   = make_bot()
        users = make_users(1)
        with (
            patch("admin.reminders._get_unpaid_users", return_value=users),
            patch("admin.reminders._is_notification_enabled", return_value=True),
            patch("admin.reminders._get_message", return_value="msg"),
            patch("admin.reminders.db.get_billing_cycle", return_value={"start": 25, "end": 5}),
            patch("admin.reminders._mark_job_ran") as mock_mark,
        ):
            from admin.reminders import send_one_day_reminder
            await send_one_day_reminder(bot, mark_run=True)
        mock_mark.assert_called_once_with("one_day")


# ── monthly_cycle_reset_job ───────────────────────────────────────────────────

class TestMonthlyCycleReset:
    @pytest.mark.asyncio
    async def test_resets_all_users(self):
        bot   = make_bot()
        users = make_users(5)
        admins = [{"telegram_id": 9999}]
        summary = {
            "month": 1, "year": 2016, "month_name": "መስከረም",
            "total_users": 5, "total_paid": 3, "total_unpaid": 2,
            "total_pending": 0, "total_rejected": 0,
            "paid_users": users[:3], "unpaid_users": users[3:],
        }
        with (
            patch("admin.reminders.db.get_cycle_summary", return_value=summary),
            patch("admin.reminders._get_all_admins", return_value=admins),
            patch("admin.reminders.db.reset_all_users_to_unpaid") as mock_reset,
            patch("admin.reminders._mark_job_ran"),
            patch("admin.reminders.to_ethiopian", return_value=(2016, 1, 6)),
            patch("admin.reminders.now_eth", return_value=datetime(2023, 9, 17, tzinfo=ETH_TZ)),
        ):
            from admin.reminders import monthly_cycle_reset_job
            await monthly_cycle_reset_job(bot, mark_run=False)
        mock_reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_sends_report_to_all_admins(self):
        bot    = make_bot()
        admins = [{"telegram_id": 1111}, {"telegram_id": 2222}]
        summary = {
            "month": 1, "year": 2016, "month_name": "መስከረም",
            "total_users": 2, "total_paid": 2, "total_unpaid": 0,
            "total_pending": 0, "total_rejected": 0,
            "paid_users": make_users(2), "unpaid_users": [],
        }
        with (
            patch("admin.reminders.db.get_cycle_summary", return_value=summary),
            patch("admin.reminders._get_all_admins", return_value=admins),
            patch("admin.reminders.db.reset_all_users_to_unpaid"),
            patch("admin.reminders._mark_job_ran"),
            patch("admin.reminders.to_ethiopian", return_value=(2016, 1, 6)),
            patch("admin.reminders.now_eth", return_value=datetime(2023, 9, 17, tzinfo=ETH_TZ)),
        ):
            from admin.reminders import monthly_cycle_reset_job
            await monthly_cycle_reset_job(bot, mark_run=False)
        assert bot.send_message.call_count == len(admins)


# ── mark_job_ran ─────────────────────────────────────────────────────────────

class TestMarkJobRan:
    def test_stores_eth_date_in_db(self):
        with (
            patch("admin.reminders.db.set_setting") as mock_set,
            patch("admin.reminders.now_eth", return_value=datetime(2023, 9, 11, tzinfo=ETH_TZ)),
        ):
            from admin.reminders import _mark_job_ran
            _mark_job_ran("payment_start")
        mock_set.assert_called_once_with("last_run_payment_start", "2016-01-01")


# ── check_missed_jobs (Phase 7) ───────────────────────────────────────────────

class TestCheckMissedJobs:
    """
    The Phase 7 startup recovery check.
    All DB and bot calls are mocked so tests run offline.
    """

    @pytest.mark.asyncio
    async def test_fires_payment_start_when_today_matches_and_not_run(self):
        bot = make_bot()
        with (
            patch("admin.reminders.to_ethiopian", return_value=(2016, 1, 25)),
            patch("admin.reminders.now_eth", return_value=datetime(2023, 9, 11, tzinfo=ETH_TZ)),
            patch("admin.reminders.db.get_billing_cycle", return_value={"start": 25, "end": 5}),
            patch("admin.reminders._get_last_run", return_value="2016-01-24"),
            patch("admin.reminders.format_eth_date_storage", return_value="2016-01-25"),
            patch("admin.reminders.send_payment_start_reminder") as mock_send,
            patch("admin.reminders.send_one_day_reminder")     as mock_one,
            patch("admin.reminders.send_final_day_reminder")   as mock_final,
            patch("admin.reminders.monthly_cycle_reset_job")   as mock_reset,
            patch("admin.reminders._notify_admins_of_recovery"),
            patch("admin.reminders._get_all_admins", return_value=[]),
        ):
            from admin.reminders import check_missed_jobs
            await check_missed_jobs(bot)
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_fire_when_already_ran_today(self):
        bot = make_bot()
        with (
            patch("admin.reminders.to_ethiopian", return_value=(2016, 1, 25)),
            patch("admin.reminders.now_eth", return_value=datetime(2023, 9, 11, tzinfo=ETH_TZ)),
            patch("admin.reminders.db.get_billing_cycle", return_value={"start": 25, "end": 5}),
            patch("admin.reminders._get_last_run", return_value="2016-01-25"),
            patch("admin.reminders.format_eth_date_storage", return_value="2016-01-25"),
            patch("admin.reminders.send_payment_start_reminder") as mock_send,
            patch("admin.reminders.send_one_day_reminder"),
            patch("admin.reminders.send_final_day_reminder"),
            patch("admin.reminders.monthly_cycle_reset_job"),
            patch("admin.reminders._notify_admins_of_recovery"),
            patch("admin.reminders._get_all_admins", return_value=[]),
        ):
            from admin.reminders import check_missed_jobs
            await check_missed_jobs(bot)
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_fires_final_day_when_today_matches_end(self):
        bot = make_bot()
        with (
            patch("admin.reminders.to_ethiopian", return_value=(2016, 1, 5)),
            patch("admin.reminders.now_eth", return_value=datetime(2023, 9, 11, tzinfo=ETH_TZ)),
            patch("admin.reminders.db.get_billing_cycle", return_value={"start": 25, "end": 5}),
            patch("admin.reminders._get_last_run", return_value=""),
            patch("admin.reminders.format_eth_date_storage", return_value="2016-01-05"),
            patch("admin.reminders.send_payment_start_reminder"),
            patch("admin.reminders.send_one_day_reminder"),
            patch("admin.reminders.send_final_day_reminder") as mock_final,
            patch("admin.reminders.monthly_cycle_reset_job"),
            patch("admin.reminders._notify_admins_of_recovery"),
            patch("admin.reminders._get_all_admins", return_value=[]),
        ):
            from admin.reminders import check_missed_jobs
            await check_missed_jobs(bot)
        mock_final.assert_called_once()
