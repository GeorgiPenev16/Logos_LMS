#!/usr/bin/env python3
"""
import_contacts.py — Import Logos borrowers / guarantors into Odoo res.partner.

Reads a structured Excel workbook (3 sheets) and creates or updates partner
records via JSON-RPC.  Dry-run by default — pass --apply to write.

Sheets
------
  Contacts   — one row per partner (company or individual)
  Income     — monthly income lines  (linked to Contacts by row_id)
  Expenses   — monthly expense lines (linked to Contacts by row_id)

Usage
-----
    python scripts/import_contacts.py --template            # generate blank template
    python scripts/import_contacts.py                       # dry-run from contacts_import.xlsx
    python scripts/import_contacts.py --apply               # write to Odoo
    python scripts/import_contacts.py --file my_data.xlsx  # custom file path

Environment variables (override defaults)
-----------------------------------------
    ODOO_URL   ODOO_DB   ODOO_USER   ODOO_PASS
"""

import os
import sys
import requests

# openpyxl is standard for Excel I/O; install: pip install openpyxl
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

ODOO_URL  = os.getenv('ODOO_URL',  'https://logos-staging.odoo.com')
ODOO_DB   = os.getenv('ODOO_DB',   'logos-staging')
ODOO_USER = os.getenv('ODOO_USER', 'admin')
ODOO_PASS = os.getenv('ODOO_PASS', 'admin')

DEFAULT_FILE = 'contacts_import.xlsx'
TEST_MODE    = True   # flipped by --apply

# ─────────────────────────────────────────────────────────────────────────────
# EXCEL TEMPLATE DEFINITION
# ─────────────────────────────────────────────────────────────────────────────

# Contacts sheet columns: (header, width, example_company, example_individual)
CONTACTS_COLS = [
    # ID / type
    ('row_id',           8,  '1',        '2'),
    ('type',             12, 'company',  'individual'),
    # Core identity
    ('name',             35, 'Алфа ЕООД', 'Иван Иванов'),
    ('company_registry', 14, '123456782', ''),       # EIK — companies only
    ('bulstat',          14, '123456782', ''),       # BULSTAT — optional
    ('personal_number',  14, '',         '7601121234'),  # EGN — individuals only
    ('id_card',          14, '',         '123456789'),
    # Roles
    ('is_loan_borrower', 16, 'yes',      'yes'),
    ('is_guarantor',     14, 'no',       'no'),
    ('is_codebtor',      12, 'no',       'no'),
    # МОЛ (company representative) — fill manager_egn to link to existing individual
    ('manager_name',     30, 'Петър Петров', ''),
    ('manager_egn',      14, '7501011234',   ''),
    # Contact info
    ('phone',            16, '+359 2 123 4567', '+359 88 123 4567'),
    ('mobile',           16, '',              '+359 88 987 6543'),
    ('email',            30, 'office@alfa.bg', 'ivan@mail.bg'),
    # Address
    ('street',           30, 'ул. Витоша 10', 'ул. Раковски 5'),
    ('city',             20, 'София',          'Пловдив'),
    ('postcode',         10, '1000',           '4000'),
    ('settlement_name',  25, 'София',          'Пловдив'),   # EKATTE lookup (optional)
    # Financial
    ('bank_account',     26, 'BG80BNBG96611020345678', ''),
    ('payment_method',   16, 'bank_transfer',           'cash'),
    # Notes
    ('ref',              14, 'ALFA-001',  'IVI-001'),
    ('notes',            40, '',          ''),
]

# Income sheet columns
INCOME_COLS = [
    ('contact_row_id', 14, '2',       '2'),
    ('type',           25, 'Заплата', 'Наем'),
    ('amount',         14, '2500.00', '500.00'),
]

# Expense sheet columns
EXPENSE_COLS = [
    ('contact_row_id', 14, '2',         '2'),
    ('type',           25, 'Кредит',    'Лизинг'),
    ('company_name',   30, 'ОББ',       'БМВ Лизинг'),
    ('amount',         14, '10000.00',  '5000.00'),
    ('monthly_payment', 14, '300.00',   '200.00'),
]

# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

HEADER_FILL  = PatternFill('solid', fgColor='1F497D')
EXAMPLE_FILL = PatternFill('solid', fgColor='EBF1DE')
HEADER_FONT  = Font(color='FFFFFF', bold=True)
REQUIRED_FONT = Font(color='FFFFFF', bold=True, italic=True)  # marks required cols


def _write_sheet(wb, title, col_defs):
    """Write header + two example rows to a sheet."""
    ws = wb.create_sheet(title)
    # Required column names (bold italic header to hint)
    required = {'row_id', 'type', 'name'}

    for col_idx, (colname, width, ex1, ex2) in enumerate(col_defs, start=1):
        cell = ws.cell(row=1, column=col_idx, value=colname)
        cell.fill  = HEADER_FILL
        cell.font  = REQUIRED_FONT if colname in required else HEADER_FONT
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[get_column_letter(col_idx)].width = width

        ws.cell(row=2, column=col_idx, value=ex1).fill = EXAMPLE_FILL
        ws.cell(row=3, column=col_idx, value=ex2).fill = EXAMPLE_FILL

    ws.freeze_panes = 'A2'
    return ws


def generate_template(filename):
    """Write a blank Excel template to filename."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)                       # remove default Sheet

    _write_sheet(wb, 'Contacts', CONTACTS_COLS)
    _write_sheet(wb, 'Income',   INCOME_COLS)
    _write_sheet(wb, 'Expenses', EXPENSE_COLS)

    # Add a Notes sheet with instructions
    ws_notes = wb.create_sheet('Notes')
    instructions = [
        ('INSTRUCTIONS', ),
        ('',),
        ('Contacts sheet',),
        ('  row_id        — unique integer per row; used to link Income and Expenses rows',),
        ('  type          — "company" or "individual"',),
        ('  name          — full legal name (required)',),
        ('  company_registry — 9-digit EIK (companies only)',),
        ('  personal_number  — 10-digit EGN (individuals only)',),
        ('  is_loan_borrower / is_guarantor / is_codebtor — "yes" or "no"',),
        ('  manager_name / manager_egn — МОЛ for company partners',),
        ('    if manager_egn matches an existing individual row, they are linked',),
        ('    otherwise a minimal individual record is created for the manager',),
        ('  settlement_name — EKATTE settlement name (optional, looked up in Odoo)',),
        ('  payment_method — "cash" or "bank_transfer"',),
        ('',),
        ('Income sheet',),
        ('  contact_row_id — must match a row_id in Contacts',),
        ('  type           — income source label (e.g. Заплата, Наем)',),
        ('  amount         — monthly amount in EUR',),
        ('',),
        ('Expenses sheet',),
        ('  contact_row_id  — must match a row_id in Contacts',),
        ('  type            — expense type label',),
        ('  company_name    — creditor name',),
        ('  amount          — outstanding balance',),
        ('  monthly_payment — monthly instalment',),
        ('',),
        ('Deduplication',),
        ('  Companies:   matched by company_registry (EIK) then name',),
        ('  Individuals: matched by personal_number (EGN) then name',),
        ('  Existing records are UPDATED with new values from Excel.',),
    ]
    for r, row in enumerate(instructions, start=1):
        ws_notes.cell(row=r, column=1, value=row[0])
    ws_notes.column_dimensions['A'].width = 80

    wb.save(filename)
    print(f'Template written to: {filename}')
    print('Fill in your data then run without --template to import.')


# ─────────────────────────────────────────────────────────────────────────────
# JSON-RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_session = None
_uid     = None


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
    resp = _session.post(f'{ODOO_URL}/web/dataset/call_kw', json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        msg = data['error'].get('data', {}).get('message', str(data['error']))
        raise RuntimeError(f'{model}.{method} → {msg}')
    return data['result']


def log(msg):
    prefix = '[DRY-RUN] ' if TEST_MODE else '[APPLY]   '
    print(prefix + msg)


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL READER
# ─────────────────────────────────────────────────────────────────────────────

def _bool(val):
    """Normalise 'yes'/'no'/True/False/1/0 → bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ('yes', 'true', '1', 'да')
    return False


def _str(val):
    """Strip and return string, or empty string."""
    if val is None:
        return ''
    return str(val).strip()


def read_sheet(ws):
    """Return list of dicts from a worksheet (row 1 = headers)."""
    headers = [_str(ws.cell(row=1, column=c).value) for c in range(1, ws.max_column + 1)]
    rows = []
    for r in range(2, ws.max_row + 1):
        row = {}
        empty = True
        for c, header in enumerate(headers, start=1):
            val = ws.cell(row=r, column=c).value
            row[header] = val
            if val not in (None, ''):
                empty = False
        if not empty:
            row['_excel_row'] = r
            rows.append(row)
    return rows


def load_workbook(filename):
    """Load workbook and return (contacts, income, expenses) as lists of dicts."""
    try:
        wb = openpyxl.load_workbook(filename, data_only=True)
    except FileNotFoundError:
        print(f'ERROR: File not found: {filename}')
        print('Generate a template first with --template, or specify --file <path>.')
        sys.exit(1)

    missing = [s for s in ('Contacts', 'Income', 'Expenses') if s not in wb.sheetnames]
    if missing:
        print(f'ERROR: Missing sheet(s): {", ".join(missing)}')
        sys.exit(1)

    return (
        read_sheet(wb['Contacts']),
        read_sheet(wb['Income']),
        read_sheet(wb['Expenses']),
    )


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_egn(egn):
    """Return True if EGN is valid (length + checksum)."""
    import re
    from datetime import date as _date
    if not re.match(r'^\d{10}$', egn):
        return False
    yp, mp, dp = int(egn[0:2]), int(egn[2:4]), int(egn[4:6])
    if   41 <= mp <= 52: year, month = 2000 + yp, mp - 40
    elif 21 <= mp <= 32: year, month = 1800 + yp, mp - 20
    elif  1 <= mp <= 12: year, month = 1900 + yp, mp
    else: return False
    try:
        _date(year, month, dp)
    except ValueError:
        return False
    weights = [2, 4, 8, 5, 10, 9, 7, 3, 6]
    total = sum(int(egn[i]) * weights[i] for i in range(9)) % 11
    return (total % 10) == int(egn[9])


def validate_eik(eik):
    """Return True if EIK (9-digit) checksum is valid."""
    if not (isinstance(eik, str) and eik.isdigit() and len(eik) == 9):
        return False
    def _check(weights):
        total = sum(int(eik[i]) * weights[i] for i in range(8)) % 11
        return total if total < 10 else None
    r1 = _check([1, 2, 3, 4, 5, 6, 7, 8])
    if r1 is not None:
        return r1 == int(eik[8])
    r2 = _check([3, 4, 5, 6, 7, 8, 9, 10])
    check = r2 % 11 if r2 is not None else 0
    return (check % 10) == int(eik[8])


def validate_rows(contacts, income, expenses):
    """
    Validate all rows.  Returns (errors, warnings) — both lists of strings.
    Import proceeds only if errors is empty.
    """
    errors   = []
    warnings = []
    row_ids  = set()

    def err(row, msg):
        errors.append(f'  Row {row}: {msg}')

    def warn(row, msg):
        warnings.append(f'  Row {row} (warning): {msg}')

    for c in contacts:
        r    = c.get('_excel_row', '?')
        rid  = _str(c.get('row_id'))
        ctype = _str(c.get('type')).lower()
        name  = _str(c.get('name'))

        if not rid:
            err(r, 'row_id is required')
        elif rid in row_ids:
            err(r, f'duplicate row_id: {rid}')
        else:
            row_ids.add(rid)

        if ctype not in ('company', 'individual'):
            err(r, f'type must be "company" or "individual", got: "{ctype}"')
        if not name:
            err(r, 'name is required')

        if ctype == 'company':
            eik = _str(c.get('company_registry'))
            if eik and not validate_eik(eik):
                err(r, f'invalid EIK checksum: {eik}')
            if _str(c.get('personal_number')):
                warn(r, 'personal_number (EGN) set on company row — will be ignored')
        elif ctype == 'individual':
            egn = _str(c.get('personal_number'))
            if egn and not validate_egn(egn):
                err(r, f'invalid EGN checksum: {egn}')
            if _str(c.get('company_registry')):
                warn(r, 'company_registry (EIK) set on individual row — will be ignored')

        pm = _str(c.get('payment_method')).lower()
        if pm and pm not in ('cash', 'bank_transfer'):
            err(r, f'payment_method must be "cash" or "bank_transfer", got: "{pm}"')

    for row in income:
        r   = row.get('_excel_row', '?')
        cid = _str(row.get('contact_row_id'))
        if not cid:
            err(r, '[Income] contact_row_id is required')
        elif cid not in row_ids:
            err(r, f'[Income] contact_row_id {cid} not found in Contacts')
        amt = row.get('amount')
        if amt is not None:
            try:
                float(amt)
            except (ValueError, TypeError):
                err(r, f'[Income] amount must be numeric, got: {amt}')

    for row in expenses:
        r   = row.get('_excel_row', '?')
        cid = _str(row.get('contact_row_id'))
        if not cid:
            err(r, '[Expenses] contact_row_id is required')
        elif cid not in row_ids:
            err(r, f'[Expenses] contact_row_id {cid} not found in Contacts')

    return errors, warnings


# ─────────────────────────────────────────────────────────────────────────────
# ODOO LOOKUPS  (cached)
# ─────────────────────────────────────────────────────────────────────────────

_settlement_cache = None   # name_bg → id
_country_bg_id    = None
_state_cache      = {}     # settlement_id → state_id


def _load_settlement_cache():
    global _settlement_cache
    if _settlement_cache is None:
        recs = call('bg.settlement', 'search_read',
                    [[]],
                    {'fields': ['id', 'name_bg'], 'limit': 10000})
        _settlement_cache = {r['name_bg'].lower(): r['id'] for r in recs}
    return _settlement_cache


def lookup_settlement(name):
    """Return settlement id or None."""
    if not name:
        return None
    cache = _load_settlement_cache()
    return cache.get(name.strip().lower())


def _find_partner_by_egn(egn):
    if not egn:
        return None
    ids = call('res.partner', 'search', [[['personal_number', '=', egn]]])
    return ids[0] if ids else None


def _find_partner_by_eik(eik):
    if not eik:
        return None
    ids = call('res.partner', 'search', [[['company_registry', '=', eik]]])
    return ids[0] if ids else None


def _find_partner_by_name(name):
    if not name:
        return None
    ids = call('res.partner', 'search', [[['name', '=', name]]])
    return ids[0] if ids else None


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def _build_partner_vals(row):
    """Build vals dict for res.partner from a Contacts row dict."""
    ctype = _str(row.get('type')).lower()
    is_company = (ctype == 'company')

    vals = {
        'name':             _str(row.get('name')),
        'is_company':       is_company,
        'is_loan_borrower': _bool(row.get('is_loan_borrower')),
        'is_guarantor':     _bool(row.get('is_guarantor')),
        'is_codebtor':      _bool(row.get('is_codebtor')),
    }

    # Optional scalar fields
    for src, dst in [
        ('phone',        'phone'),
        ('mobile',       'mobile'),
        ('email',        'email'),
        ('street',       'street'),
        ('city',         'city'),
        ('postcode',     'zip'),
        ('bank_account', 'bank_account'),
        ('ref',          'ref'),
        ('notes',        'comment'),
    ]:
        v = _str(row.get(src))
        if v:
            vals[dst] = v

    # payment_method
    pm = _str(row.get('payment_method')).lower()
    if pm in ('cash', 'bank_transfer'):
        vals['payment_method'] = pm

    if is_company:
        eik = _str(row.get('company_registry'))
        if eik:
            vals['company_registry'] = eik
        bulstat = _str(row.get('bulstat'))
        if bulstat:
            vals['bulstat'] = bulstat
    else:
        egn = _str(row.get('personal_number'))
        if egn:
            vals['personal_number'] = egn
        id_card = _str(row.get('id_card'))
        if id_card:
            vals['id_card'] = id_card

    # EKATTE settlement lookup
    sname = _str(row.get('settlement_name'))
    if sname:
        sid = lookup_settlement(sname)
        if sid:
            vals['settlement_id'] = sid
        else:
            log(f'    WARNING: settlement "{sname}" not found in EKATTE — skipping settlement_id')

    return vals


def _upsert_partner(row, existing_id, label):
    """Create or update a partner. Returns partner_id."""
    vals = _build_partner_vals(row)
    name = vals.get('name', '?')

    if existing_id:
        log(f'  UPDATE {label} "{name}" (id={existing_id})')
        if not TEST_MODE:
            call('res.partner', 'write', [[existing_id], vals])
        return existing_id
    else:
        log(f'  CREATE {label} "{name}"')
        if not TEST_MODE:
            new_id = call('res.partner', 'create', [vals])
            return new_id
        return None   # dry-run: no real id


def _get_or_create_manager(manager_name, manager_egn):
    """
    Look up or create an individual partner for a company's МОЛ.
    Returns partner_id or None.
    """
    if not manager_name and not manager_egn:
        return None

    # Try to find by EGN first, then by name
    existing_id = None
    if manager_egn:
        existing_id = _find_partner_by_egn(manager_egn)
    if not existing_id and manager_name:
        existing_id = _find_partner_by_name(manager_name)

    if existing_id:
        log(f'    МОЛ: found existing partner id={existing_id}')
        return existing_id

    # Create minimal individual record
    log(f'    МОЛ: creating individual "{manager_name}"')
    if not TEST_MODE:
        vals = {'name': manager_name, 'is_company': False}
        if manager_egn:
            vals['personal_number'] = manager_egn
        new_id = call('res.partner', 'create', [vals])
        return new_id
    return None


def import_contacts(contacts, income, expenses):
    """
    Main import logic.  Returns row_id → partner_id mapping.
    """
    # ── Pass 1: individual contacts (needed first so managers can be linked) ──

    row_id_to_partner_id = {}   # str row_id → int odoo id (or None in dry-run)

    def _process_row(row):
        r    = row.get('_excel_row', '?')
        rid  = _str(row.get('row_id'))
        ctype = _str(row.get('type')).lower()
        is_company = (ctype == 'company')

        # Find existing partner
        existing_id = None
        if is_company:
            eik = _str(row.get('company_registry'))
            existing_id = _find_partner_by_eik(eik) if eik else None
            if not existing_id:
                existing_id = _find_partner_by_name(_str(row.get('name')))
            label = 'company'
        else:
            egn = _str(row.get('personal_number'))
            existing_id = _find_partner_by_egn(egn) if egn else None
            if not existing_id:
                existing_id = _find_partner_by_name(_str(row.get('name')))
            label = 'individual'

        try:
            partner_id = _upsert_partner(row, existing_id, label)
        except RuntimeError as e:
            log(f'  ERROR row {r}: {e}')
            return rid, None

        # МОЛ (only for companies, in apply mode)
        if is_company and partner_id:
            mgr_name = _str(row.get('manager_name'))
            mgr_egn  = _str(row.get('manager_egn'))
            mgr_id   = _get_or_create_manager(mgr_name, mgr_egn)
            if mgr_id and not TEST_MODE:
                call('res.partner', 'write', [[partner_id], {'manager_id': mgr_id}])

        return rid, partner_id

    print('\n── Contacts ────────────────────────────────────────────────────')

    # Process individuals first (managers may need to exist before companies)
    for row in contacts:
        if _str(row.get('type')).lower() == 'individual':
            rid, pid = _process_row(row)
            row_id_to_partner_id[rid] = pid

    # Then companies
    for row in contacts:
        if _str(row.get('type')).lower() == 'company':
            rid, pid = _process_row(row)
            row_id_to_partner_id[rid] = pid

    log(f'Contacts: {len(row_id_to_partner_id)} processed.')

    # ── Pass 2: Income lines ──────────────────────────────────────────────────

    print('\n── Income Lines ────────────────────────────────────────────────')
    income_count = 0
    for row in income:
        r   = row.get('_excel_row', '?')
        cid = _str(row.get('contact_row_id'))
        itype = _str(row.get('type'))
        amt   = row.get('amount')

        partner_id = row_id_to_partner_id.get(cid)
        if partner_id is None and not TEST_MODE:
            log(f'  SKIP income row {r}: no partner_id for contact_row_id={cid}')
            continue

        vals = {
            'type':        itype,
            'amount':      float(amt) if amt else 0.0,
            'customer_id': partner_id or 0,
        }
        log(f'  income: partner_id={partner_id or "(dry-run)"}  type={itype}  amount={vals["amount"]}')
        if not TEST_MODE and partner_id:
            call('customer.income.line', 'create', [vals])
        income_count += 1

    log(f'Income lines: {income_count} processed.')

    # ── Pass 3: Expense lines ─────────────────────────────────────────────────

    print('\n── Expense Lines ───────────────────────────────────────────────')
    expense_count = 0
    for row in expenses:
        r   = row.get('_excel_row', '?')
        cid = _str(row.get('contact_row_id'))
        etype = _str(row.get('type'))
        cname = _str(row.get('company_name'))
        amt   = row.get('amount')
        mp    = row.get('monthly_payment')

        partner_id = row_id_to_partner_id.get(cid)
        if partner_id is None and not TEST_MODE:
            log(f'  SKIP expense row {r}: no partner_id for contact_row_id={cid}')
            continue

        vals = {
            'type':            etype,
            'company_name':    cname,
            'amount':          float(amt) if amt else 0.0,
            'monthly_payment': float(mp)  if mp  else 0.0,
            'customer_id':     partner_id or 0,
        }
        log(f'  expense: partner_id={partner_id or "(dry-run)"}  type={etype}  amount={vals["amount"]}')
        if not TEST_MODE and partner_id:
            call('customer.expense.line', 'create', [vals])
        expense_count += 1

    log(f'Expense lines: {expense_count} processed.')

    return row_id_to_partner_id


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global TEST_MODE

    args = sys.argv[1:]

    # ── --template: generate blank Excel and exit ─────────────────────────────
    if '--template' in args:
        filename = DEFAULT_FILE
        for i, a in enumerate(args):
            if a == '--file' and i + 1 < len(args):
                filename = args[i + 1]
        generate_template(filename)
        return

    # ── Determine file and mode ───────────────────────────────────────────────
    filename = DEFAULT_FILE
    for i, a in enumerate(args):
        if a == '--file' and i + 1 < len(args):
            filename = args[i + 1]

    if '--apply' in args:
        TEST_MODE = False

    mode = 'DRY-RUN (no changes written)' if TEST_MODE else 'APPLY MODE (writing to Odoo)'
    print(f'import_contacts.py — {mode}')
    print(f'File:   {filename}')
    print(f'Target: {ODOO_URL}  DB: {ODOO_DB}')

    # ── Load Excel ────────────────────────────────────────────────────────────
    contacts, income, expenses = load_workbook(filename)
    print(f'\nLoaded: {len(contacts)} contacts, {len(income)} income rows, '
          f'{len(expenses)} expense rows.')

    # ── Validate ──────────────────────────────────────────────────────────────
    print('\n── Validation ──────────────────────────────────────────────────')
    errors, warnings = validate_rows(contacts, income, expenses)

    for w in warnings:
        print('  WARN ' + w)
    for e in errors:
        print('  ERR  ' + e)

    if errors:
        print(f'\n{len(errors)} validation error(s) found. Fix the Excel file and retry.')
        sys.exit(1)
    else:
        print('  Validation passed.')

    # ── Connect and import ────────────────────────────────────────────────────
    connect()
    print(f'Authenticated as uid={_uid}')

    import_contacts(contacts, income, expenses)

    print('\nDone.')
    if TEST_MODE:
        print('Re-run with --apply to write changes to Odoo.')


if __name__ == '__main__':
    main()
