#!/usr/bin/env python3
"""
Generic Odoo configuration for Logos LMS.

Sets up:
  1. Bulgarian public holidays 2026-2035
       - resource.calendar.leaves  (used by _adjust_due_date() / _get_bg_holidays())
       - public.holidays            (used by base module _get_valid_installment_date())
  2. LMS penalty settings on res.company (skip-if-already-set)
  3. Standard loan document types

Usage:
    python scripts/setup_generic.py            # dry-run (TEST_MODE=True)
    python scripts/setup_generic.py --apply    # write to Odoo

Environment variables (override defaults):
    ODOO_URL   ODOO_DB   ODOO_USER   ODOO_PASS
"""

import os
import sys
import requests
from datetime import date, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

ODOO_URL  = os.getenv('ODOO_URL',  'https://logos-staging.odoo.com')
ODOO_DB   = os.getenv('ODOO_DB',   'logos-staging')
ODOO_USER = os.getenv('ODOO_USER', 'admin')
ODOO_PASS = os.getenv('ODOO_PASS', 'admin')

TEST_MODE = True

HOLIDAY_YEARS = list(range(2026, 2036))   # 2026–2035 inclusive (10 years)

# Fixed Bulgarian national holidays — (month, day, Bulgarian name)
# Source: КТ чл.154 ал.1
FIXED_HOLIDAYS = [
    ( 1,  1, 'Нова година'),
    ( 3,  3, 'Ден на Освобождението на България'),
    ( 5,  1, 'Ден на труда'),
    ( 5,  6, 'Гергьовден'),
    ( 5, 24, 'Ден на просветата'),
    ( 9,  6, 'Ден на Съединението'),
    ( 9, 22, 'Ден на Независимостта'),
    (12, 24, 'Бъдни вечер'),
    (12, 25, 'Рождество Христово'),
    (12, 26, 'Рождество Христово (2-ри ден)'),
]

# One-off special holidays — (date, name)
SPECIAL_HOLIDAYS = [
    (date(2026, 1, 2), 'Еднократен почивен ден — въвеждане на EUR'),
]

# LMS penalty defaults — written to res.company (skipped if field already non-zero)
PENALTY_DEFAULTS = {
    'lms_penalty_rate_annual': 0.1015,   # 10.15% = ECB main rate + 8 pp (Постановление № 426/2014)
    'lms_penalty_divisor':     365,      # A/365F convention
    'lms_penalty_grace_days':  0,        # days after emi_date before penalty starts
}

# Standard loan document types for customer.document.type
DOCUMENT_TYPES = [
    'Лична карта',
    'Удостоверение за доходи',
    'Трудов договор',
    'Служебна бележка',
    'ЕИК / Удостоверение за регистрация',
    'Счетоводен баланс',
    'Отчет за приходите и разходите',
    'Нотариален акт / Договор за наем',
]

# ─────────────────────────────────────────────────────────────────────────────
# JSON-RPC HELPERS  (same pattern as setup_logos.py)
# ─────────────────────────────────────────────────────────────────────────────

_session = None
_uid = None


def connect():
    global _session, _uid
    _session = requests.Session()
    payload = {
        'jsonrpc': '2.0', 'method': 'call', 'id': 1,
        'params': {'db': ODOO_DB, 'login': ODOO_USER, 'password': ODOO_PASS},
    }
    resp = _session.post(f'{ODOO_URL}/web/session/authenticate', json=payload, timeout=30)
    resp.raise_for_status()
    uid = resp.json().get('result', {}).get('uid')
    if not uid:
        print('ERROR: Authentication failed. Check ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS.')
        sys.exit(1)
    _uid = uid


def call(model, method, args=None, kwargs=None):
    payload = {
        'jsonrpc': '2.0', 'method': 'call', 'id': 1,
        'params': {
            'model': model, 'method': method,
            'args': args or [], 'kwargs': kwargs or {},
        },
    }
    resp = _session.post(f'{ODOO_URL}/web/dataset/call_kw', json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        msg = data['error'].get('data', {}).get('message', data['error'])
        print(f'ERROR: {model}.{method} → {msg}')
        sys.exit(1)
    return data['result']


def log(msg):
    prefix = '[DRY-RUN] ' if TEST_MODE else '[APPLY]   '
    print(prefix + msg)


def write_or_log(model, rec_id, vals, description):
    log(f'{description}  →  {model}[{rec_id}]  vals={vals}')
    if not TEST_MODE:
        call(model, 'write', [[rec_id], vals])


# ─────────────────────────────────────────────────────────────────────────────
# HOLIDAY CALCULATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def orthodox_easter(year):
    """
    Orthodox Easter date in Gregorian calendar.
    Uses Julian calendar algorithm then adds 13 days (21st century offset).

    Verified:
      2025 → Apr 20 | 2026 → Apr 12 | 2027 → May 2
      2028 → Apr 16 | 2029 → Apr 8  | 2030 → Apr 28
    """
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day   = (d + e + 114) % 31 + 1
    julian = date(year, month, day)
    return julian + timedelta(days=13)


def build_holiday_list(years):
    """
    Build sorted list of (date, name) covering all years.

    Includes:
    - 10 fixed national holidays per year (КТ чл.154 ал.1)
    - 4 Easter days: Good Friday, Holy Saturday, Easter Sunday, Easter Monday
    - One-off special holidays (e.g. Jan 2 2026 for EUR introduction)
    - Weekend compensations: КТ чл.154 ал.2
        Saturday holiday → following Monday off
        Sunday holiday   → following Monday off
        (skipped if that Monday is already a holiday)

    Note: Official government decrees (МС) may specify different compensation
    days in some years. Review output in dry-run mode before applying.
    """
    result = []

    for year in years:
        # Use dict to deduplicate by date within each year
        year_dates = {}

        # Fixed national holidays
        for month, day, name in FIXED_HOLIDAYS:
            year_dates[date(year, month, day)] = name

        # Orthodox Easter — 4 days (КТ чл.154 ал.1 т.9)
        easter = orthodox_easter(year)
        year_dates[easter - timedelta(days=2)] = 'Велики петък'
        year_dates[easter - timedelta(days=1)] = 'Велика събота'
        year_dates[easter]                     = 'Великден'
        year_dates[easter + timedelta(days=1)] = 'Понеделник на Великден'

        # Special one-off holidays
        for d, name in SPECIAL_HOLIDAYS:
            if d.year == year:
                year_dates[d] = name

        # КТ чл.154 ал.2 — weekend compensation
        # Iterate a snapshot so we don't compensate compensations
        compensations = {}
        for d, name in list(year_dates.items()):
            if d.weekday() == 5:       # Saturday → next Monday (+2)
                comp = d + timedelta(days=2)
            elif d.weekday() == 6:     # Sunday → next Monday (+1)
                comp = d + timedelta(days=1)
            else:
                continue
            # Only add if: stays in same year AND not already a holiday
            if comp.year == year and comp not in year_dates:
                compensations[comp] = (
                    f'Почивен ден (компенсация за {d.strftime("%d.%m")})'
                )

        year_dates.update(compensations)
        result.extend(year_dates.items())

    result.sort(key=lambda x: x[0])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Holidays
# ─────────────────────────────────────────────────────────────────────────────

def setup_holidays():
    print('\n── Holidays ────────────────────────────────────────────────────')

    all_holidays = build_holiday_list(HOLIDAY_YEARS)
    print(f'   Coverage: {HOLIDAY_YEARS[0]}–{HOLIDAY_YEARS[-1]} '
          f'({len(all_holidays)} entries including compensations)')

    # ── 1a: resource.calendar.leaves ─────────────────────────────────────────
    # Used by _adjust_due_date() / _get_bg_holidays() in tk_loan_management_bg
    print('\n   [resource.calendar.leaves]')

    company_ids = call('res.company', 'search', [[]])
    company = call('res.company', 'read',
                   [[company_ids[0]], ['name', 'resource_calendar_id']])[0]
    cal = company.get('resource_calendar_id')
    calendar_id = cal[0] if cal else None

    if not calendar_id:
        log('   WARNING: Company has no work calendar — skipping resource.calendar.leaves.')
    else:
        existing_leaves = call(
            'resource.calendar.leaves', 'search_read',
            [[['calendar_id', '=', calendar_id]]],
            {'fields': ['date_from'], 'limit': 5000},
        )
        existing_dates = {r['date_from'][:10] for r in existing_leaves}

        created = skipped = 0
        for d, name in all_holidays:
            ds = d.strftime('%Y-%m-%d')
            if ds in existing_dates:
                skipped += 1
                continue
            log(f'   {ds}  {name}')
            if not TEST_MODE:
                call('resource.calendar.leaves', 'create', [{
                    'name':        name,
                    'calendar_id': calendar_id,
                    'date_from':   f'{ds} 00:00:00',
                    'date_to':     f'{ds} 23:59:59',
                    'time_type':   'leave',
                }])
            created += 1

        log(f'   resource.calendar.leaves: {created} to create, {skipped} already exist.')

    # ── 1b: public.holidays (base module) ────────────────────────────────────
    # Used by base _get_valid_installment_date() / _get_public_holiday_dates()
    print('\n   [public.holidays — base module]')

    existing_ph = call(
        'public.holidays', 'search_read',
        [[]],
        {'fields': ['start_date'], 'limit': 5000},
    )
    existing_ph_dates = {r['start_date'] for r in existing_ph}

    created_p = skipped_p = 0
    for d, name in all_holidays:
        ds = d.strftime('%Y-%m-%d')
        if ds in existing_ph_dates:
            skipped_p += 1
            continue
        log(f'   {ds}  {name}')
        if not TEST_MODE:
            new_id = call('public.holidays', 'create', [{
                'name':       name,
                'start_date': ds,
                'end_date':   ds,
            }])
            call('public.holidays', 'action_confirm', [[new_id]])
        created_p += 1

    log(f'   public.holidays: {created_p} to create, {skipped_p} already exist.')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Penalty Settings
# ─────────────────────────────────────────────────────────────────────────────

def setup_penalty_settings():
    print('\n── Penalty Settings ────────────────────────────────────────────')

    company_ids = call('res.company', 'search', [[]])
    company_id  = company_ids[0]
    company_data = call('res.company', 'read',
                        [[company_id], list(PENALTY_DEFAULTS.keys())])[0]

    to_write = {}
    for field, default_val in PENALTY_DEFAULTS.items():
        current = company_data.get(field)
        # Skip if already set to a meaningful value
        if current and current not in (0, 0.0, False, None):
            log(f'   Skip {field}: already {current}')
        else:
            log(f'   Set  {field}: {default_val}')
            to_write[field] = default_val

    if to_write:
        write_or_log('res.company', company_id, to_write, 'Penalty settings')
    else:
        log('   All penalty settings already configured.')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Document Types
# ─────────────────────────────────────────────────────────────────────────────

def setup_document_types():
    print('\n── Document Types ──────────────────────────────────────────────')

    for name in DOCUMENT_TYPES:
        existing = call('customer.document.type', 'search', [[['name', '=', name]]])
        if existing:
            log(f'   Skip (exists): {name}')
        else:
            log(f'   Create: {name}')
            if not TEST_MODE:
                call('customer.document.type', 'create', [{'name': name}])

    log('Document types done.')


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global TEST_MODE
    if '--apply' in sys.argv:
        TEST_MODE = False

    mode = 'DRY-RUN (no changes written)' if TEST_MODE else 'APPLY MODE (writing to Odoo)'
    print(f'setup_generic.py — {mode}')
    print(f'Target: {ODOO_URL}  DB: {ODOO_DB}')

    connect()
    print(f'Authenticated as uid={_uid}')

    setup_holidays()
    setup_penalty_settings()
    setup_document_types()

    print('\nDone.')
    if TEST_MODE:
        print('Re-run with --apply to write changes to Odoo.')


if __name__ == '__main__':
    main()
