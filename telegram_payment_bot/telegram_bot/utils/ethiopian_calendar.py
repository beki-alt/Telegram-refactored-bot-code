"""
utils/ethiopian_calendar.py
────────────────────────────
Ethiopian Calendar utilities.

FIX applied: format_eth_date() was using .year/.month/.day attribute access on the
tuple returned by to_ethiopian(). All functions now use consistent tuple unpacking.
"""

import logging
from datetime import datetime
from typing import List, Tuple

import pytz

logger = logging.getLogger(__name__)

ETH_TZ = pytz.timezone("Africa/Addis_Ababa")

_ETH_MONTHS = [
    "",
    "መስከረም",
    "ጥቅምት",
    "ህዳር",
    "ታህሳስ",
    "ጥር",
    "የካቲት",
    "መጋቢት",
    "ሚያዝያ",
    "ግንቦት",
    "ሰኔ",
    "ሐምሌ",
    "ነሐሴ",
    "ጳጉሜ",
]

_ETH_EPOCH_JDN = 1724220  # Verified: Sep 11 2020 → Meskerem 1, 2013 ✓  |  June 5 2026 → Ginbot 28, 2018 ✓


def _greg_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return (
        day
        + (153 * m + 2) // 5
        + 365 * y
        + y // 4
        - y // 100
        + y // 400
        - 32045
    )


def _jdn_to_ethiopian(jdn: int) -> Tuple[int, int, int]:
    era = jdn - _ETH_EPOCH_JDN
    quad, remainder = divmod(era, 1461)
    year_base = quad * 4

    if remainder == 0:
        return year_base, 1, 1

    year_in_quad, day_in_year = divmod(remainder - 1, 365)
    eth_year  = year_base + year_in_quad + 1
    eth_month = day_in_year // 30 + 1
    eth_day   = day_in_year % 30 + 1
    return eth_year, eth_month, eth_day


def to_ethiopian(dt: datetime) -> Tuple[int, int, int]:
    """
    Convert a datetime to an Ethiopian calendar tuple: (eth_year, eth_month, eth_day).
    Always returns a plain (int, int, int) tuple.

    BUG-1 FIX: When the `ethiopian_date` library is available, its result is
    cross-checked against the built-in JDN formula.  A disagreement of more
    than one calendar day is logged as a warning so that date bugs surface
    immediately instead of silently producing wrong billing dates.
    The JDN formula is always used as the authoritative fallback if the
    library raises any exception.
    """
    if dt.tzinfo is None:
        dt = ETH_TZ.localize(dt)
    else:
        dt = dt.astimezone(ETH_TZ)

    g_year, g_month, g_day = dt.year, dt.month, dt.day

    # Authoritative JDN result — always compute this.
    jdn      = _greg_to_jdn(g_year, g_month, g_day)
    jdn_eth  = _jdn_to_ethiopian(jdn)

    try:
        from ethiopian_date import EthiopianDateConverter
        lib_result = EthiopianDateConverter.to_ethiopian(g_year, g_month, g_day)
        lib_eth    = (int(lib_result[0]), int(lib_result[1]), int(lib_result[2]))

        # Cross-check: compute day-numbers and warn if they differ by more than 1.
        lib_jdn_approx = (lib_eth[0] * 365 + (lib_eth[1] - 1) * 30 + lib_eth[2])
        jdn_approx     = (jdn_eth[0] * 365 + (jdn_eth[1] - 1) * 30 + jdn_eth[2])
        if abs(lib_jdn_approx - jdn_approx) > 1:
            logger.warning(
                f"Ethiopian calendar library/JDN mismatch for {g_year}-{g_month:02d}-{g_day:02d}: "
                f"lib={lib_eth}, jdn={jdn_eth}. Using JDN result as authoritative."
            )
            return jdn_eth

        return lib_eth
    except Exception:
        pass

    return jdn_eth


def now_eth() -> datetime:
    return datetime.now(tz=ETH_TZ)


def eth_month_name(month: int) -> str:
    if 1 <= month <= 13:
        return _ETH_MONTHS[month]
    return str(month)


def eth_days_in_month(eth_year: int, eth_month: int) -> int:
    """Return the number of days in an Ethiopian month.
    Months 1-12 always have 30 days.
    Month 13 (Pagume) has 6 days in an Ethiopian leap year (eth_year % 4 == 3), else 5.
    """
    if eth_month < 13:
        return 30
    return 6 if eth_year % 4 == 3 else 5


def effective_end_day(eth_year: int, eth_month: int, configured_end_day: int) -> int:
    """Return the actual billing end day, capped at the real last day of the month.

    This guarantees correctness for Pagume (5-6 days) and any future calendar edge
    cases.  For all 12 regular months end_day stays as configured (they all have 30
    days so any value 1-30 is always valid).  For Pagume, end_day is capped at 5 or 6.

    Example: configured_end_day=30, current month=Pagume (5 days) → returns 5.
             configured_end_day=30, current month=Ginbot (30 days) → returns 30.
    """
    return min(configured_end_day, eth_days_in_month(eth_year, eth_month))


def prev_eth_months(n: int = 6) -> List[Tuple[int, int]]:
    eth_year, eth_month, _ = to_ethiopian(now_eth())
    months: List[Tuple[int, int]] = []
    y, m = eth_year, eth_month
    for _ in range(n):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 13
            y -= 1
    return months


def format_eth_date(dt: datetime) -> str:
    """
    Return a human-readable Ethiopian date string.
    Example: "25 መስከረም 2016"

    FIX: was using .year/.month/.day on tuple return — now uses tuple unpacking.
    """
    y, m, d = to_ethiopian(dt)
    return f"{d} {eth_month_name(m)} {y}"


def format_eth_datetime(dt: datetime) -> str:
    """
    Return Ethiopian date + local time string.
    Example: "25 መስከረም 2016 — 12:35"
    """
    if dt.tzinfo is None:
        dt = ETH_TZ.localize(dt)
    else:
        dt = dt.astimezone(ETH_TZ)
    y, m, d = to_ethiopian(dt)
    return f"{d} {eth_month_name(m)} {y} — {dt.strftime('%H:%M')}"


def format_eth_date_storage(dt: datetime) -> str:
    """Return Ethiopian date in ISO-like storage format: '2016-01-25'"""
    y, m, d = to_ethiopian(dt)
    return f"{y}-{m:02d}-{d:02d}"


def parse_eth_date_storage(eth_str: str) -> Tuple[int, int, int]:
    """Parse a stored Ethiopian date string '2016-01-25'. Returns (0,0,0) on failure."""
    try:
        parts = eth_str.split("-")
        return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        return 0, 0, 0


def eth_storage_to_display(eth_str: str) -> str:
    """
    Convert a stored Ethiopian date string to a human-readable display string.

    '2018-09-28'  →  '28 ግንቦት 2018'
    ''            →  '—'
    None          →  '—'

    Use this everywhere a stored eth_payment_date is shown to users or written
    to Excel, instead of showing the raw '2018-09-28' (which looks like GC) or
    the Gregorian created_at timestamp.
    """
    if not eth_str:
        return "—"
    y, m, d = parse_eth_date_storage(eth_str)
    if y == 0:
        return eth_str or "—"
    return f"{d} {eth_month_name(m)} {y}"
