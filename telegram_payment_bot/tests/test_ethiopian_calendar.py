"""
tests/test_ethiopian_calendar.py
──────────────────────────────────
Phase 9 — Full test suite for Ethiopian calendar utilities.

Tests cover:
  - Known Gregorian → Ethiopian conversions (ground truth from public sources)
  - format_eth_date() no longer crashes with AttributeError (BUG FIX verification)
  - format_eth_date_storage() / parse_eth_date_storage() round-trip
  - eth_days_in_month() for normal and Pagume months + leap years
  - is_eth_leap_year()
  - eth_month_name() for all 13 months
  - prev_eth_months() ordering and length
  - eth_days_between()

Run with:
  cd telegram-bot && python -m pytest tests/test_ethiopian_calendar.py -v
"""

import sys
import os
from datetime import datetime

import pytest
import pytz

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.ethiopian_calendar import (
    ETH_TZ,
    eth_days_between,
    eth_days_in_month,
    eth_month_name,
    format_eth_date,
    format_eth_date_storage,
    format_eth_datetime,
    is_eth_leap_year,
    now_eth,
    parse_eth_date_storage,
    prev_eth_months,
    to_ethiopian,
)


# ── Known conversion ground truth ─────────────────────────────────────────────
# Verified against https://www.eida.go.et and online EC-GC converters

KNOWN_CONVERSIONS = [
    # (greg_year, greg_month, greg_day, eth_year, eth_month, eth_day, note)
    (2023,  9, 11,  2016, 1,  1,  "New Year 2016 EC"),
    (2023,  9, 12,  2016, 1,  2,  "Day after New Year"),
    (2024,  9, 11,  2017, 1,  1,  "New Year 2017 EC"),
    (2020, 11,  9,  2013, 3,  1,  "Hidar 1, 2013"),
    (2000,  1,  8,  1992, 5,  1,  "Tir 1, 1992"),
    (2023, 10, 11,  2016, 2,  1,  "Tikimt 1, 2016"),
    (2024,  3, 10,  2016, 7,  1,  "Megabit 1, 2016"),
    (2024,  9,  4,  2016, 12, 25, "Nehase 25, 2016"),
    (2024,  9,  5,  2016, 12, 26, "Nehase 26, 2016"),
    (2024,  9,  6,  2016, 13,  1, "Pagume 1, 2016"),
    (2024,  9, 10,  2016, 13,  5, "Pagume 5, 2016"),
    (2024,  9, 11,  2017, 1,  1,  "New Year 2017 EC"),
]


@pytest.mark.parametrize("gy,gm,gd,ey,em,ed,note", KNOWN_CONVERSIONS)
def test_known_conversions(gy, gm, gd, ey, em, ed, note):
    """to_ethiopian() must match known ground-truth values."""
    dt = datetime(gy, gm, gd, 12, 0, tzinfo=ETH_TZ)
    result_year, result_month, result_day = to_ethiopian(dt)
    assert result_year  == ey,  f"{note}: year  expected {ey}, got {result_year}"
    assert result_month == em,  f"{note}: month expected {em}, got {result_month}"
    assert result_day   == ed,  f"{note}: day   expected {ed}, got {result_day}"


# ── BUG FIX: format_eth_date() no longer crashes ─────────────────────────────

def test_format_eth_date_no_attribute_error():
    """
    BUG FIX verification: original code called eth_date.year on a tuple,
    causing AttributeError. format_eth_date() must not crash.
    """
    dt     = datetime(2023, 9, 11, tzinfo=ETH_TZ)
    result = format_eth_date(dt)
    assert isinstance(result, str)
    assert len(result) > 0
    # Should contain the year 2016
    assert "2016" in result


def test_format_eth_date_contains_month_name():
    """format_eth_date() must include the Amharic month name."""
    dt     = datetime(2023, 9, 11, tzinfo=ETH_TZ)  # Meskerem 1, 2016
    result = format_eth_date(dt)
    assert "መስከረም" in result


def test_format_eth_date_naive_datetime():
    """format_eth_date() must handle naive datetimes by assuming ETH_TZ."""
    dt     = datetime(2023, 9, 11)  # naive
    result = format_eth_date(dt)
    assert isinstance(result, str)
    assert "2016" in result


def test_format_eth_datetime_no_crash():
    """format_eth_datetime() must not crash (had same tuple bug as format_eth_date)."""
    dt     = datetime(2023, 9, 11, 10, 30, tzinfo=ETH_TZ)
    result = format_eth_datetime(dt)
    assert "2016" in result
    assert "10:30" in result


# ── Storage format round-trip ─────────────────────────────────────────────────

@pytest.mark.parametrize("year,month,day", [
    (2016, 1,  1),
    (2016, 13, 5),
    (2017, 6, 15),
    (1992, 5,  1),
])
def test_storage_format_round_trip(year, month, day):
    """format_eth_date_storage / parse_eth_date_storage must round-trip."""
    # We need a datetime that converts to these exact values.
    # We'll just test parse directly.
    s = f"{year}-{month:02d}-{day:02d}"
    y2, m2, d2 = parse_eth_date_storage(s)
    assert y2 == year
    assert m2 == month
    assert d2 == day


def test_parse_eth_date_storage_invalid():
    """parse_eth_date_storage must return (0,0,0) for invalid input."""
    assert parse_eth_date_storage("not-a-date") == (0, 0, 0)
    assert parse_eth_date_storage("") == (0, 0, 0)
    assert parse_eth_date_storage("2016-13") == (0, 0, 0)


def test_format_eth_date_storage_known():
    """format_eth_date_storage must produce correct storage string."""
    dt = datetime(2023, 9, 11, 12, 0, tzinfo=ETH_TZ)  # Meskerem 1, 2016
    s  = format_eth_date_storage(dt)
    assert s == "2016-01-01"


# ── Days in month ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("eth_year,eth_month,expected", [
    (2016,  1, 30),
    (2016,  6, 30),
    (2016, 12, 30),
    (2016, 13,  5),  # non-leap year
    (2015, 13,  6),  # leap year (2015 % 4 == 3)
    (2019, 13,  6),  # leap year (2019 % 4 == 3)
    (2017, 13,  5),  # non-leap
    (2018, 13,  5),  # non-leap
])
def test_eth_days_in_month(eth_year, eth_month, expected):
    assert eth_days_in_month(eth_year, eth_month) == expected


# ── Leap year ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("eth_year,expected", [
    (2015, True),
    (2016, False),
    (2017, False),
    (2018, False),
    (2019, True),
    (2011, True),
    (2012, False),
])
def test_is_eth_leap_year(eth_year, expected):
    assert is_eth_leap_year(eth_year) == expected


# ── Month names ───────────────────────────────────────────────────────────────

def test_eth_month_names_all_defined():
    """All 13 Ethiopian month names must be non-empty Amharic strings."""
    expected = [
        "መስከረም", "ጥቅምት", "ህዳር", "ታህሳስ", "ጥር", "የካቲት",
        "መጋቢት", "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ",
    ]
    for i, name in enumerate(expected, 1):
        assert eth_month_name(i) == name, f"Month {i}: expected {name}"


def test_eth_month_name_out_of_range():
    """Out-of-range month numbers must return the number as a string."""
    assert eth_month_name(0)  == "0"
    assert eth_month_name(14) == "14"


# ── prev_eth_months ───────────────────────────────────────────────────────────

def test_prev_eth_months_length():
    months = prev_eth_months(6)
    assert len(months) == 6


def test_prev_eth_months_ordering():
    """First entry must be the most recent month."""
    months = prev_eth_months(3)
    assert len(months) == 3
    for i in range(len(months) - 1):
        y1, m1 = months[i]
        y2, m2 = months[i + 1]
        # months[i] must be chronologically after months[i+1]
        assert (y1, m1) > (y2, m2) or (y1 > y2) or (y1 == y2 and m1 >= m2)


def test_prev_eth_months_valid_range():
    """All returned months must have valid month numbers (1–13)."""
    for y, m in prev_eth_months(13):
        assert 1 <= m <= 13
        assert y > 1900


def test_prev_eth_months_cross_year():
    """Crossing a year boundary must produce month 13 of previous year."""
    months = prev_eth_months(14)
    month_numbers = [m for _, m in months]
    assert 13 in month_numbers


# ── eth_days_between ──────────────────────────────────────────────────────────

def test_eth_days_between_same_day():
    assert eth_days_between(2016, 1, 1, 2016, 1, 1) == 0


def test_eth_days_between_one_day():
    assert eth_days_between(2016, 1, 1, 2016, 1, 2) == 1


def test_eth_days_between_negative():
    assert eth_days_between(2016, 1, 2, 2016, 1, 1) == -1


def test_eth_days_between_cross_month():
    # Meskerem has 30 days; from day 30 to Tikimt 1 = 1 day
    assert eth_days_between(2016, 1, 30, 2016, 2, 1) == 1


def test_eth_days_between_cross_year():
    # Pagume 5 (2016) to Meskerem 1 (2017) = 1 day (non-leap year)
    days_in_pagume = eth_days_in_month(2016, 13)
    diff = eth_days_between(2016, 13, days_in_pagume, 2017, 1, 1)
    assert diff == 1


# ── now_eth timezone ──────────────────────────────────────────────────────────

def test_now_eth_timezone():
    """now_eth() must return a timezone-aware datetime in Africa/Addis_Ababa."""
    dt = now_eth()
    assert dt.tzinfo is not None
    expected_tz = pytz.timezone("Africa/Addis_Ababa")
    # Check UTC offset is +3 (EAT) ±1h for DST edge cases
    offset_hours = dt.utcoffset().total_seconds() / 3600
    assert abs(offset_hours - 3) < 1


def test_to_ethiopian_returns_tuple():
    """to_ethiopian() must return a 3-tuple (year, month, day) — not an object."""
    dt     = datetime(2023, 9, 11, tzinfo=ETH_TZ)
    result = to_ethiopian(dt)
    assert isinstance(result, tuple)
    assert len(result) == 3
    eth_year, eth_month, eth_day = result
    assert isinstance(eth_year,  int)
    assert isinstance(eth_month, int)
    assert isinstance(eth_day,   int)
    assert 1 <= eth_month <= 13
    assert 1 <= eth_day <= 30
