# Claude Code Project Context

## PROJECT
**VitoshaBG Loan Management Framework**
- **Client:** Logos (loan company, Bulgaria)
- **Base Module:** `tk_loan_management` by TechKhedut (OPL-1 license - **never modify directly**)
- **Custom Module:** `tk_loan_management_bg` (VitoshaBG additions - inherits base module)
- **Odoo Version:** 19
- **Base Module Version:** 1.0.8 (staging) — upgraded from 1.0.6
- **Repo Path:** `C:\Odoo\Logos_LMS-staging` (canonical), `C:\Odoo\LMS_21072025` (original/archive)

## ARCHITECTURE RULE
- **Never modify `tk_loan_management` files directly** — they are under OPL-1 license
- All additions go into `tk_loan_management_bg` via Odoo inheritance (`_inherit`)
- Scripts go into `/scripts` folder at project root
- Import scripts go at project root (e.g. `import_loans.py`)

## BASE MODULE STRUCTURE
Path: `tk_loan_management/`

### 14 Models
| Model | File | Purpose |
|-------|------|---------|
| `customer.loan` | `customer_loan.py` | Main loan record |
| `customer.loan.lines` | `customer_loan.py:2042` | Installment schedule lines |
| `customer.loan.document.lines` | `customer_loan.py:2167` | Uploaded documents per loan |
| `customer.collateral.lines` | `customer_loan.py:2272` | Collateral records |
| `customer.loan.installment.penalty.lines` | `customer_loan.py:2315` | Penalty tracking |
| `customer.loan.request.document` | `customer_loan.py:2354` | Document requests to customer |
| `customer.loan.request.collateral` | `customer_loan.py:2380` | Collateral requests |
| `customer.loan.sanction.latter` | `customer_loan.py:2413` | Sanction letters |
| `customer.loan.type` | `customer_loan_type.py` | Loan product configuration |
| `customer.loan.type.term.lines` | `customer_loan_type.py:97` | Term-based interest rate overrides |
| `loan.type.document.lines` | `customer_loan_type.py:133` | Required docs per loan type |
| `res.partner` (inherited) | `customer_loan_res_partner.py` | EGN, ID card, roles, codebtor |
| `account.move` (inherited) | `customer_loan_account_move.py` | Journal entry overrides |
| Helper models | `customer_loan_res_partner.py` | `customer.income.line`, `customer.expense.line`, `family.info`, `labour.relation` |

### Key Methods on `customer.loan`
- `compute_installment()` (line ~1281) — generates installment schedule
- `_calculate_emi()` (line ~1448) — PMT formula, signature: `(self, loan_amount, interest_rate, term, installment_type, is_grace_period)`
- `_generate_loan_schedule()` (line ~1363) — creates loan lines with dates
- `action_disburse_loan()` (line ~1683) — creates disbursement journal entry
- `action_create_journal_entry()` (line ~2120) — on `customer.loan.lines`, creates repayment entry
- `action_recalculate_installment()` (line ~1619) — **v1.0.8** prepayment: removes unpaid installments, creates prepayment JE, regenerates schedule
- `_generate_recalculated_installment()` (line ~1724) — **v1.0.8** helper for post-prepayment schedule
- `action_send_recalculate_mail()` (line ~1806) — **v1.0.8** sends revised schedule email after prepayment

### Status Workflow
`draft` → `confirm` → `dept_approval` → `confirmation` → `disbursement` → `in_progress` → `closure`/`pre_closure`/`settlement`

### Accounting Fields on Loan
- `receivable_account_id` — account_type='asset_receivable'
- `bank_cash_account` — account_type='asset_cash'
- `interest_income_account_id` — account_type='asset_receivable'
- `journal_item_id` — disbursement journal
- `repayment_journal_item_id` — repayment journal
- `journal_entry_id` — the disbursement journal entry

### 3 Cron Jobs
1. **Loan Reminders** — sends email before installment due date
2. **Penalty Application** — applies penalties on overdue installments
3. **Compound Interest** — calculates compound interest on overdue amounts

## WHAT THE BASE MODULE HAS
- Full Bulgarian translation (bg.po, ~95% coverage)
- EGN validation (10-digit Bulgarian personal number with checksum)
- ID card validation (9 digits or 2 uppercase letters + 7 digits)
- Installment schedule generation (monthly/quarterly/yearly)
- Disbursement and repayment journal entries (automated)
- Penalty system (fixed amount or percentage)
- Sanction letter workflow (send → sign → expire)
- Document and collateral management
- Grace period support
- Holiday-aware date calculation
- Number-to-words in Bulgarian (for contracts)
- **v1.0.8:** Loan prepayment with automatic installment recalculation
- **v1.0.8:** Payment wizard (`loan.payment`) with allocation logic (interest → penalty → fee → principal)
- **v1.0.8:** Revised schedule email notification after prepayment
- **v1.0.8:** Overdue penalty interest config on loan type (`is_overdue_penalty_interest`, `od_penalty_interest`)
- **v1.0.8:** Enhanced JE tracking flags on `account.move.line` (`is_interest`, `is_principal`, `is_fee`, `is_overdue_interest`)
- **v1.0.8:** Controllers for portal, website lead form, and sanction letter signing

## KNOWN GAPS (what `tk_loan_management_bg` must fix)
1. **No company/EIK support** — all partners treated as individuals, EGN always required
2. **No guarantor role on loan** — `is_codebtor` exists on partner but loan has no codebtor/guarantor field
3. **No ГПР/XIRR calculation** — only simple PMT formula, no APR/IRR/total cost of credit
4. **Contract company info hardcoded** — "Finance Hold Bulgaria" with specific EIK baked into template
5. **Codebtor not linked to loan** — `codebtor_ids` is partner-to-partner M2M, not on `customer.loan`
6. **No domain enforcement on codebtor role** — any partner can be added regardless of `is_codebtor` flag
7. **No AnaCredit reporting fields**
8. **Installments not editable** after generation

> **Note:** v1.0.8 partially addresses installment recalculation via prepayment wizard, but
> installment grid fields remain non-editable for manual corrections.

## WHAT `tk_loan_management_bg` MUST ADD
1. Company borrower support (ЕИК, MOL/МОЛ, БУЛСТАТ)
2. Guarantor role (Поръчител) linked to loan
3. ГПР/XIRR calculation (Bulgarian law requirement, max 50%)
4. Dynamic contract template (editable by admin, company info from settings)
5. Editable installments grid
6. Improved Bulgarian translations
7. AnaCredit reporting fields

## SCRIPTS
| Script | Purpose |
|--------|---------|
| `setup_generic.py` | Journals, document types, holidays, settings |
| `setup_logos.py` | Logos-specific configuration |
| `import_contacts.py` | Borrower data from Excel |
| `import_loans.py` | Loan migration with paid installments marked |

## LOGOS CLIENT SPECIFICS
- Mostly company borrowers (not individuals)
- 20-100 active loans to migrate
- Data currently in their own software
- Needs backdated loan entry with paid installments marked

## BULGARIAN COMPLIANCE REQUIREMENTS
- ГПР mandatory on every contract (max 50%)
- ЕИК for companies (9 or 13 digits with checksum)
- EGN for individuals (10 digits with checksum)
- BGN/EUR dual currency (fixed rate 1.95583)
- Sequential invoice numbering

## DEVELOPMENT RULES
- Always use `TEST_MODE = True` by default in scripts
- Field labels must be in Bulgarian
- Never hardcode company-specific data — use `res.company` or `ir.config_parameter`
- All company info must come from settings, not baked into templates
- Prefer editing existing files over creating new ones
- Never modify files inside `tk_loan_management/`
