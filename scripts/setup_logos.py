#!/usr/bin/env python3
"""
Logos-specific Odoo configuration script.

Sets up all Logos company data via JSON-RPC:
  - Currency: EUR active, BGN inactive
  - Company currency set to EUR
  - Loan types with Logos-specific parameters

Usage:
    python scripts/setup_logos.py            # dry-run (TEST_MODE=True)
    python scripts/setup_logos.py --apply    # actually write to Odoo

Environment variables (override defaults):
    ODOO_URL   — e.g. https://logos-staging.odoo.com
    ODOO_DB    — e.g. logos-staging
    ODOO_USER  — e.g. admin
    ODOO_PASS  — admin password
"""

import os
import sys
import requests

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  (override via environment variables)
# ─────────────────────────────────────────────────────────────────────────────

ODOO_URL  = os.getenv('ODOO_URL',  'https://logos-staging.odoo.com')
ODOO_DB   = os.getenv('ODOO_DB',   'logos-staging')
ODOO_USER = os.getenv('ODOO_USER', 'admin')
ODOO_PASS = os.getenv('ODOO_PASS', 'admin')

TEST_MODE = True   # Set False (or pass --apply) to actually write records

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_session = None   # requests.Session — reused for all calls (carries cookies)
_uid = None


def connect():
    """Authenticate via JSON-RPC and return uid."""
    global _session, _uid
    _session = requests.Session()
    payload = {
        'jsonrpc': '2.0',
        'method': 'call',
        'id': 1,
        'params': {
            'db':       ODOO_DB,
            'login':    ODOO_USER,
            'password': ODOO_PASS,
        },
    }
    resp = _session.post(f'{ODOO_URL}/web/session/authenticate', json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    uid = result.get('result', {}).get('uid')
    if not uid:
        print('ERROR: Authentication failed. Check ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS.')
        sys.exit(1)
    _uid = uid
    return uid


def call(model, method, args=None, kwargs=None):
    """Execute an ORM method via JSON-RPC /web/dataset/call_kw."""
    payload = {
        'jsonrpc': '2.0',
        'method': 'call',
        'id': 1,
        'params': {
            'model':  model,
            'method': method,
            'args':   args or [],
            'kwargs': kwargs or {},
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
# SECTION 1: Currency Setup
# EUR active (company currency), BGN inactive
# Reason: Bulgaria joins Eurozone 2026
# ─────────────────────────────────────────────────────────────────────────────

def setup_currencies():
    print('\n── Currency Setup ──────────────────────────────────────────────')

    # Find EUR
    eur_ids = call('res.currency', 'search', [[['name', '=', 'EUR']]])
    if not eur_ids:
        print('ERROR: EUR currency not found in Odoo. Aborting.')
        sys.exit(1)
    eur_id = eur_ids[0]

    # Find BGN
    bgn_ids = call('res.currency', 'search', [[['name', '=', 'BGN']]])
    bgn_id = bgn_ids[0] if bgn_ids else None

    # Activate EUR
    write_or_log('res.currency', eur_id, {'active': True}, 'Activate EUR')

    # Deactivate BGN
    if bgn_id:
        write_or_log('res.currency', bgn_id, {'active': False}, 'Deactivate BGN')
    else:
        log('BGN not found — skipping deactivation')

    # Set company currency to EUR
    company_ids = call('res.company', 'search', [[]])
    if not company_ids:
        print('ERROR: No company found. Aborting.')
        sys.exit(1)
    company_id = company_ids[0]

    company_data = call('res.company', 'read', [[company_id], ['name', 'currency_id']])[0]
    log(f"Company: {company_data['name']}  current currency: {company_data['currency_id']}")

    write_or_log('res.company', company_id,
                 {'currency_id': eur_id},
                 f'Set company currency to EUR (id={eur_id})')

    log('Currency setup complete.')
    return eur_id


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Loan Types
# Logos-specific loan products. All amounts in EUR (€).
# ─────────────────────────────────────────────────────────────────────────────

LOAN_TYPES = [
    {
        'name':        'Стандартен потребителски кредит',
        'description': (
            'Потребителски кредит от 500 € до 15 000 €. '
            'Срок: 6–60 месеца. '
            'Лихвен процент: от 12% годишно. '
            'Месечна вноска зависи от сумата и срока.'
        ),
        'min_loan_amount': 500.0,
        'max_loan_amount': 15000.0,
        'min_term': 6,
        'max_term': 60,
        'interest_rate': 12.0,
    },
    {
        'name':        'Бизнес кредит',
        'description': (
            'Кредит за юридически лица от 5 000 € до 100 000 €. '
            'Срок: 12–84 месеца. '
            'Лихвен процент: от 10% годишно. '
            'Изисква се ЕИК и финансови отчети.'
        ),
        'min_loan_amount': 5000.0,
        'max_loan_amount': 100000.0,
        'min_term': 12,
        'max_term': 84,
        'interest_rate': 10.0,
    },
    {
        'name':        'Бърз кредит',
        'description': (
            'Краткосрочен кредит от 200 € до 3 000 €. '
            'Срок: 3–24 месеца. '
            'Лихвен процент: от 18% годишно. '
            'Одобрение до 24 часа.'
        ),
        'min_loan_amount': 200.0,
        'max_loan_amount': 3000.0,
        'min_term': 3,
        'max_term': 24,
        'interest_rate': 18.0,
    },
]


def setup_loan_types():
    print('\n── Loan Types ──────────────────────────────────────────────────')

    for lt in LOAN_TYPES:
        name = lt['name']
        existing = call('customer.loan.type', 'search', [[['name', '=', name]]])
        vals = {
            'name':          lt['name'],
            'description':   lt['description'],
            'interest_rate': lt['interest_rate'],
        }

        if existing:
            log(f"Update loan type '{name}' (id={existing[0]})")
            write_or_log('customer.loan.type', existing[0], vals, f"Update '{name}'")
        else:
            log(f"Create loan type '{name}'")
            if not TEST_MODE:
                new_id = call('customer.loan.type', 'create', [vals])
                log(f'  Created id={new_id}')

    log('Loan types setup complete.')


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global TEST_MODE
    if '--apply' in sys.argv:
        TEST_MODE = False

    mode_label = 'DRY-RUN (no changes written)' if TEST_MODE else 'APPLY MODE (writing to Odoo)'
    print(f'setup_logos.py — {mode_label}')
    print(f'Target: {ODOO_URL}  DB: {ODOO_DB}')

    connect()
    print(f'Authenticated as uid={_uid}')

    setup_currencies()
    setup_loan_types()

    print('\nDone.')
    if TEST_MODE:
        print('Re-run with --apply to write changes to Odoo.')


if __name__ == '__main__':
    main()
