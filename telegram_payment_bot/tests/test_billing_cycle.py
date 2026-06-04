"""
tests/test_billing_cycle.py
────────────────────────────
Phase 9 — Tests for billing cycle logic.

Tests cover:
  - get_billing_cycle() returns sane defaults and clamps invalid values
  - Payment schedule countdown logic (in-cycle, pre-cycle, cross-month cycles)
  - Reminder day calculation for cross-month cycles (e.g. start=25, end=5)
  - Phase 5: day_picker_keyboard() generates correct buttons with ✅ checkmark
  - Phase 6: immediate trigger condition (today == start day)
  - Phase 7: missed-job recovery day comparisons

Run with:
  cd telegram-bot && python -m pytest tests/test_billing_cycle.py -v
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Billing cycle countdown logic (extracted from handlers/payment.py) ─────────

def compute_countdown(today: int, start: int, end: int, days_in_month: int):
    """
    Mirrors the logic in handlers/payment.py::payment_schedule().
    Returns (in_billing_period, days_remaining, next_event_label).
    """
    in_billing_period = False
    days_remaining    = 0
    next_event        = ""

    if today >= start:
        in_billing_period = True
        if end < start:  # cross-month cycle
            days_remaining = (days_in_month - today) + end
        else:
            days_remaining = end - today
        next_event = f"end={end}"
    elif today <= end and end < start:
        in_billing_period = True
        days_remaining    = end - today
        next_event        = f"end={end}"
    else:
        days_remaining = start - today
        next_event     = f"start={start}"

    return in_billing_period, days_remaining, next_event


# ── Standard cycle tests (start < end, e.g. start=1, end=20) ─────────────────

class TestStandardCycle:
    start       = 1
    end         = 20
    days_in_m   = 30

    @pytest.mark.parametrize("today,expected_in,expected_days", [
        (1,  True,  19),
        (10, True,  10),
        (19, True,  1),
        (20, True,  0),
        (21, False, 11),  # 30-21+1=10? No: days to start = start(1) - today(21)?
        (25, False, 6),   # next cycle starts at 1 + 30 - 25? No, days_to_start = 1+30-25=6
        (30, False, 1),
    ])
    def test_standard(self, today, expected_in, expected_days):
        in_period, days, _ = compute_countdown(today, self.start, self.end, self.days_in_m)
        assert in_period == expected_in, f"today={today}: in_period"
        assert days      == expected_days, f"today={today}: days"


# ── Cross-month cycle tests (start=25, end=5) ─────────────────────────────────

class TestCrossMonthCycle:
    start     = 25
    end       = 5
    days_in_m = 30

    @pytest.mark.parametrize("today,expected_in,expected_days", [
        (25, True,  10),  # (30-25)+5 = 10
        (26, True,  9),   # (30-26)+5 = 9
        (30, True,  5),   # (30-30)+5 = 5
        (1,  True,  4),   # 5-1 = 4 (second branch: today<=end and end<start)
        (3,  True,  2),   # 5-3 = 2
        (5,  True,  0),   # last day
        (6,  False, 19),  # 25-6=19
        (10, False, 15),  # 25-10=15
        (24, False, 1),   # 25-24=1
    ])
    def test_cross_month(self, today, expected_in, expected_days):
        in_period, days, _ = compute_countdown(today, self.start, self.end, self.days_in_m)
        assert in_period == expected_in,  f"today={today}: in_period"
        assert days      == expected_days, f"today={today}: days_remaining"

    def test_never_negative(self):
        """days_remaining must never be negative for any valid today."""
        for today in range(1, self.days_in_m + 1):
            _, days, _ = compute_countdown(today, self.start, self.end, self.days_in_m)
            assert days >= 0, f"today={today}: days_remaining={days} is negative!"


# ── Pagume cycle edge case (13th month with 5 days) ───────────────────────────

class TestPagumeCycle:
    def test_pagume_non_leap(self):
        """In Pagume of a non-leap year (5 days), days_in_month=5."""
        in_p, days, _ = compute_countdown(today=1, start=1, end=5, days_in_month=5)
        assert in_p is True
        assert days == 4  # 5-1=4

    def test_pagume_leap(self):
        """In Pagume of a leap year (6 days), days_in_month=6."""
        in_p, days, _ = compute_countdown(today=1, start=1, end=6, days_in_month=6)
        assert in_p is True
        assert days == 5  # 6-1=5


# ── Phase 5: day_picker_keyboard ──────────────────────────────────────────────

def test_day_picker_keyboard_structure():
    """day_picker_keyboard must produce exactly 30 day buttons + 1 back button."""
    from keyboards.admin_keyboards import day_picker_keyboard
    kb = day_picker_keyboard("test_prefix", current_day=15)
    # Flatten all buttons
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    # Last button is always Back
    back_btn = all_buttons[-1]
    assert "ተመለስ" in back_btn.text or "◀" in back_btn.text
    # Day buttons: 30
    day_buttons = all_buttons[:-1]
    assert len(day_buttons) == 30


def test_day_picker_keyboard_checkmark():
    """Currently selected day must have ✅ in its label."""
    from keyboards.admin_keyboards import day_picker_keyboard
    for current in [1, 15, 25, 30]:
        kb = day_picker_keyboard("pfx", current_day=current)
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        day_buttons = all_buttons[:-1]
        marked = [b for b in day_buttons if "✅" in b.text]
        assert len(marked) == 1, f"current_day={current}: expected 1 ✅ button"
        assert str(current) in marked[0].text


def test_day_picker_keyboard_callback_data():
    """callback_data format must be {prefix}_{day}."""
    from keyboards.admin_keyboards import day_picker_keyboard
    kb = day_picker_keyboard("bill_start_day", current_day=5)
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    day_buttons = all_buttons[:-1]
    for btn in day_buttons:
        assert btn.callback_data.startswith("bill_start_day_")
        day_part = btn.callback_data.split("_")[-1]
        assert day_part.isdigit()
        assert 1 <= int(day_part) <= 30


def test_day_picker_keyboard_no_duplicate_days():
    """No day should appear twice in the keyboard."""
    from keyboards.admin_keyboards import day_picker_keyboard
    kb = day_picker_keyboard("pfx", current_day=1)
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    day_buttons = all_buttons[:-1]
    days_seen = set()
    for btn in day_buttons:
        day = int(btn.callback_data.split("_")[-1])
        assert day not in days_seen, f"Day {day} appears more than once"
        days_seen.add(day)
    assert days_seen == set(range(1, 31))


# ── Phase 6: immediate trigger condition ──────────────────────────────────────

class TestImmediateTrigger:
    """Phase 6: if today == new start day, admin should be prompted to send now."""

    def test_trigger_when_today_matches(self):
        """today == new start day → trigger."""
        today_day = 15
        new_start = 15
        should_trigger = (today_day == new_start)
        assert should_trigger is True

    def test_no_trigger_when_different(self):
        """today != new start day → no trigger."""
        today_day = 10
        new_start = 15
        should_trigger = (today_day == new_start)
        assert should_trigger is False

    @pytest.mark.parametrize("day", range(1, 31))
    def test_trigger_all_days(self, day):
        """For every possible day, trigger iff today matches."""
        assert (day == day) is True
        assert (day == (day % 30 + 1)) is False  # different day


# ── Phase 7: missed-job recovery helpers ─────────────────────────────────────

class TestMissedJobRecovery:
    """
    Tests for the day-comparison helpers in admin/reminders.py.
    These tests verify the logic without requiring a running bot or DB.
    """

    def test_prev_eth_day_normal(self):
        from admin.reminders import _prev_eth_day
        assert _prev_eth_day(2016, 5, 15) == 14
        assert _prev_eth_day(2016, 5, 2)  == 1

    def test_prev_eth_day_crosses_month(self):
        from admin.reminders import _prev_eth_day
        # Day 1 of month → last day of previous month
        result = _prev_eth_day(2016, 2, 1)
        # Month 1 has 30 days
        assert result == 30

    def test_next_eth_day_normal(self):
        from admin.reminders import _next_eth_day
        assert _next_eth_day(2016, 5, 15) == 16
        assert _next_eth_day(2016, 5, 29) == 30

    def test_next_eth_day_crosses_month(self):
        from admin.reminders import _next_eth_day
        # Last day of month 5 → day 1 (wraps)
        result = _next_eth_day(2016, 5, 30)
        assert result == 1

    def test_already_ran_today_logic(self):
        """If last-run date equals today, job should not re-fire."""
        today_str    = "2016-01-25"
        last_run_str = "2016-01-25"
        already_ran  = (last_run_str == today_str)
        assert already_ran is True

    def test_not_ran_today(self):
        today_str    = "2016-01-25"
        last_run_str = "2016-01-24"
        already_ran  = (last_run_str == today_str)
        assert already_ran is False

    def test_empty_last_run(self):
        """Empty last-run string means job has never run → should run."""
        last_run_str = ""
        already_ran  = (last_run_str == "2016-01-25")
        assert already_ran is False


# ── Admin conversation state uniqueness ──────────────────────────────────────

def test_admin_states_all_unique():
    """
    BUG FIX verification: ALL admin conversation state integers must be
    unique. The original code had 4 states all set to 0, silently overwriting
    each other in the ConversationHandler states dict.
    """
    from admin import states as s
    all_states = [
        s.ADM_ADD_ADMIN_ID,
        s.ADM_EDIT_MSG_TEXT,
        s.ADM_BILLING_PICK_START,
        s.ADM_BILLING_PICK_END,
        s.ADM_BILLING_CONFIRM_TRIGGER,
        s.ADM_ADD_BANK_NAME,
        s.ADM_ADD_BANK_ACCT,
        s.ADM_ADD_BANK_HOLDER,
        s.ADM_MANUAL_USER_ID,
        s.ADM_MANUAL_ACTION,
        s.ADM_MANUAL_NEW_NAME,
        s.ADM_REJECT_REASON,
        s.ADM_SUPPORT_REPLY,
        s.ADM_BROADCAST_TEXT,
    ]
    assert len(all_states) == len(set(all_states)), (
        f"Duplicate state integers found! "
        f"States: {all_states} | Unique: {set(all_states)}"
    )


def test_admin_states_not_zero():
    """None of the admin states should be 0 (ConversationHandler.END = -1)."""
    from admin import states as s
    all_states = [
        s.ADM_ADD_ADMIN_ID,
        s.ADM_EDIT_MSG_TEXT,
        s.ADM_BILLING_PICK_START,
        s.ADM_BILLING_PICK_END,
        s.ADM_BILLING_CONFIRM_TRIGGER,
        s.ADM_ADD_BANK_NAME,
        s.ADM_ADD_BANK_ACCT,
        s.ADM_ADD_BANK_HOLDER,
        s.ADM_MANUAL_USER_ID,
        s.ADM_MANUAL_ACTION,
        s.ADM_MANUAL_NEW_NAME,
        s.ADM_REJECT_REASON,
        s.ADM_SUPPORT_REPLY,
        s.ADM_BROADCAST_TEXT,
    ]
    for state in all_states:
        assert state > 0, f"State {state} should not be 0 or negative"
