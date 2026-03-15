# Claude Code Project Context

## PROJECT
**VitoshaBG Loan Management Framework**
- **Client:** Logos (loan company, Bulgaria)
- **Base Module:** `tk_loan_management` by TechKhedut (OPL-1 license - **never modify directly**)
- **Custom Module:** `tk_loan_management_bg` (VitoshaBG additions - inherits base module)
- **Odoo Version:** 19
- **Base Module Version:** 1.0.8 (staging) — upgraded from 1.0.6
- **Custom Module Version:** 1.0.18
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

## DEVELOPMENT STATUS

### Completed
| Phase | Feature | Details |
|-------|---------|---------|
| Phase 2 | **Company/EIK support** | `company_registry` EIK validation (9-digit checksum), `bulstat` field, `manager_id` (МОЛ), skip EGN for companies |
| Phase 2 | **Guarantor role** | `is_guarantor` on `res.partner`; loan view wired up |
| Phase 4 | **ГПР/XIRR calculation** | `loan.gpr` model, XIRR method per ЗПК чл.19, max 50% enforcement |
| Phase 5 | **Dynamic document templates** | `loan.document` + `document.template` models, admin-editable, report renderer |
| Phase 6 | **Bulgarian address data** | 28 oblasts → `res.country.state`; 5,256 settlements → `bg.settlement` (ЕКАТТЕ + postcodes + coordinates + NUTS3) |
| Phase 6 | **`l10n_bg` dependency** | Evaluated — **not added** (module is self-contained; `l10n_bg` not required for address or compliance features) |
| Phase 7 | **Guarantor & Co-debtor on loan** | `customer.loan.guarantor.line` + `customer.loan.codebtor.line` models; `guarantor_line_ids` / `codebtor_line_ids` One2many on `customer.loan`; dedicated tabs in loan form; editable only in draft/confirm; domain enforces `is_guarantor`/`is_codebtor` flags |
| Phase 7 | **Represented By** | `represented_by` Many2one on `customer.loan`; visible only for company borrowers; auto-fills from `customer_id.manager_id` on change; readonly after draft |
| Phase 6 | **Settlement lookup on partner** | `settlement_id` Many2one on `res.partner`; auto-fills city, postcode, oblast, country for main address |
| Phase 6 | **Employer settlement lookup** | `ep_settlement_id` Many2one; auto-fills employer city, postcode, oblast |

### Completed Accounting Groups
| Group | Feature | Version | Commit |
|-------|---------|---------|--------|
| **A** | `res.config.settings` extension (23 `lms_` fields on `res.company`), Settings UI tab "Loans (БГ)", Bulgarian NAS chart of accounts (18 accounts, noupdate=1), 4 loan journals (LDISB/LCOL/LOPS/LINV, noupdate=1). Base module per-loan account fields hidden; auto-populated from company settings via `default_get()`. | 1.0.12 | `361bed0` `37198d7` `580c710` |
| **B** | Disbursement overhaul: `_compute_st_lt_split()` (12-month window from installment schedule), `action_disburse_loan()` override: DR 4110+262 / CR 5031. Graceful fallback to base if accounts not configured. `_create_fee_invoice_bg()` for origination fee invoice (LINV journal → 7220). | 1.0.13 | `2d91157` |
| **C** | Interest accrual cron (daily 06:00): `_cron_post_interest_accrual()` posts DR 4960 / CR 7210 per installment on due date. Fields added to `customer.loan.lines`: `accrual_move_id`, `accrual_status`. Skips gracefully if accounts not configured. | 1.0.14 | pending |
| **D** | Penalty system (cash-basis, zero GL): 6 fields on `customer.loan.lines` (`penalty_start_date`, `penalty_accrued_informational`, `penalty_calculated_at_payment`, `penalty_custom_amount`, `waive_penalty`, `paid_penalty`). Daily cron `_cron_update_penalty_informational()`. Base GL-posting crons overridden as no-ops. Account 4961 NOT used. | 1.0.15 | `cb349d2` |
| **E** | Payment wizard overhaul: global 4-round FIFO sweep (Penalty→Fee→Interest→Principal), correct BG accounts (4960/4113/4110-4112/7230), unlocked payment date, 3 penalty options (full/waived/custom), one JE per installment. Graceful fallback to base if accounts not configured. | 1.0.16 | `e27f45f` |
| **F** | Reclassification & overdue status: `days_overdue` computed; `status='overdue'` in `_compute_status`; daily cron DR 4112/CR 4110 (once per line, `overdue_reclass_move_id`); monthly cron DR 4110/CR 262 reverse+repost delta (`lt_reclass_move_id`). | 1.0.17 | `19ed298` |
| **G** | Pre-closure BG wizard: single settlement JE (4110+4112+262+4960+7230+7240), reverses future GROUP C accruals, `closure_date` + fee% fields. Decrease-term wizard: formula §11C, generates N new amortisation lines, button on loan form. | 1.0.18 | pending |

### Remaining — by group (see PLAN.md Phase 3b + ACCOUNTING_SPEC.md)
| Group | Feature | Priority |
|-------|---------|---------|
| **H** | Provision for loan losses (DPD buckets, 6290/2991) | Post go-live |
| **AC-1** | AnaCredit fields on `customer.loan` + `res.config.settings.anacredit_agent_id` | Post go-live |
| **AC-2** | `CUCR_enhanced.csv` export wizard / XML-RPC script | Post go-live |
| **AC-3** | BNB submission workflow docs + validation | Post go-live |
| — | Improved Bulgarian translations | Ongoing |

> **Note:** v1.0.8 partially addresses installment recalculation via prepayment wizard, but
> installment grid fields remain non-editable for manual corrections.

## CUSTOM MODULE MODELS (`tk_loan_management_bg`)

| Model | File | Purpose |
|-------|------|---------|
| `res.partner` (inherited) | `partner_bg.py` | EIK/BULSTAT validation, МОЛ, `is_guarantor`, settlement lookup (main + employer), EGN skip for companies |
| `customer.loan` (inherited) | `loan_bg.py` | `represented_by`, `codebtor_line_ids`, `guarantor_line_ids`, `generated_document_ids`; `default_get()` auto-fills base accounting fields from `res.company.lms_*` |
| `customer.loan` (inherited) | `loan_disburse_bg.py` | GROUP B: `_compute_st_lt_split()`, `action_disburse_loan()` override (DR 4110+262/CR 5031), `_create_fee_invoice_bg()` |
| `customer.loan.codebtor.line` | `loan_bg.py` | Co-debtor line: `partner_id` (domain `is_codebtor=True`), `guarantee_percentage` |
| `customer.loan.guarantor.line` | `loan_bg.py` | Guarantor line: `partner_id` (domain `is_guarantor=True`), `guarantee_percentage` |
| `res.company` (inherited) | `res_config_settings_bg.py` | GROUP A: 23 `lms_` fields (penalty config, journals, 14 accounts) |
| `res.config.settings` (inherited) | `res_config_settings_bg.py` | GROUP A: `related` fields exposing all `lms_*` in Settings → Loans (БГ) |
| `loan.gpr` | `loan_gpr.py` | ГПР (APR) calculation via XIRR method per ЗПК чл.19 |
| `loan.document` | `loan_document.py` | Document generation linked to loan |
| `document.template` | `document_template.py` | Admin-editable document templates |
| `bg.settlement` | `bg_settlement.py` | 5,256 Bulgarian settlements (ЕКАТТЕ) with postcode, oblast, municipality, NUTS3, lat/lng |

### `bg.settlement` Key Fields
- `ekatte` — 5-digit NSI code
- `name_bg` / `name_en` — settlement name (BG/EN)
- `type_prefix` — с. / гр. / ман. etc.
- `display_name_bg` — computed full name (prefix + name)
- `state_id` → `res.country.state` (28 oblasts)
- `mun_code` / `mun_name` — municipality
- `postcode`, `lat`, `lng`, `nuts3`
- Search by: `display_name_bg`, `name_bg`, `name_en`, `ekatte`, `postcode`

### Address auto-fill on `res.partner`
- `settlement_id` → fills `city`, `zip` (via computed `settlement_city`/`settlement_postcode`), `state_id`, `country_id`
- `ep_settlement_id` → fills employer address fields (`ep_settlement_city`, `ep_settlement_postcode`, `ep_state_id`, `ep_country_id`)
- Computed fields stored outside `o_address_format` widget to survive re-render resets

## ACCOUNTING REFERENCE

> **Primary source: `ACCOUNTING_SPEC.md`** — read before writing any accounting code.
> Entity: НФИ (non-bank financial institution). Standard: Bulgarian NAS. Currency: EUR (post 01.01.2026).

### Chart of Accounts (Bulgarian NAS)
| Account | Name | Type |
|---------|------|------|
| `262` | Дългосрочни заеми — клиенти | LT Loans Receivable |
| `4110` | Вземания по кредити — текуща вноска | ST Loans Receivable (current 12m) |
| `4112` | Просрочени вземания | Overdue Loan Principal |
| `4113` | Вземания за такси | Fees Receivable |
| `4960` | Начислени лихви | Accrued Interest Receivable |
| `4961` | Начислена наказателна лихва | Penalty Interest Receivable |
| `2991` | Провизии за загуби | Allowance for Loan Losses (contra) |
| `5030` | Разплащателна сметка — Отпускане | Bank — Disbursements |
| `5031` | Разплащателна сметка — Погашения | Bank — Collections |
| `7210` | Приходи от лихви | Interest Income |
| `7220` | Приходи от такси | Initial Fee Income |
| `7230` | Приходи от наказателни лихви | Penalty Interest Income |
| `7240` | Приходи от такси и санкции | Fee & Admin Income |
| `7250` | Приходи от данъци по кредити | Loan Tax Income |
| `6290` | Разходи за обезценка | Loan Loss Provision Expense |

### Key Journal Entries (target state — after GROUP A-E)
| Event | DR | CR |
|-------|----|----|
| Disbursement | 4110 + 262 | 5030 |
| Interest accrual (at installment date) | 4960 | 7210 |
| Penalty daily increment (Approach A cron) | 4961 | 7230 |
| Payment — penalty (cash basis) | 5031 | 7230 only (no 4961) |
| Payment — interest | 5031 | 4960 |
| Payment — fee | 5031 | 4113 / 7220 |
| Payment — principal | 5031 | 4110 / 4112 / 262 |
| Overdue reclassification | 4112 | 4110 |
| LT→ST reclassification (monthly) | 4110 | 262 |
| Provision | 6290 | 2991 |

### Penalty Rules — CASH BASIS ONLY (NEVER hardcode rates)
- Rate: `penalty_rate_annual` from `res.config.settings` (currently 10.15% = ECB+8pp)
- Divisor: `penalty_divisor` = 365 (A/365F)
- Grace days: `penalty_grace_days` from settings (default 0)
- Base: `unpaid_principal + unpaid_interest` of that installment only
- No penalty on penalty (simple interest)
- Resets to zero after any payment — recalculate from new unpaid balance
- **`4961` NOT used** — no daily GL entries
- Daily cron: informational only → `penalty_accrued_informational` (display, no JE)
- Payment wizard — **3 options**:
  1. **Full** — `penalty_calculated_at_payment` (recalculated fresh on payment date)
  2. **Waived** — `exclude_penalty = True` → `penalty_to_pay = 0`, no JE
  3. **Custom** — `penalty_custom_amount` (negotiated, staff editable, ≥ 0)
- JE posted only on cash receipt: `DR 5031 / CR 7230`

### Payment Allocation — Global 4-Round Sweep (ЗПК Art. 35)
NOT per-installment waterfall. Each round clears one component across ALL installments (oldest first):
1. **Round 1 — ALL penalties** (`DR 5031 / CR 7230` — cash basis, skip if `waive_penalty`)
2. **Round 2 — ALL fees** (`DR 5031 / CR 4113`)
3. **Round 3 — ALL interest** (`DR 5031 / CR 4960` — clears accrued)
4. **Round 4 — Principal FIFO** (`DR 5031 / CR 4112` if overdue, else `4110`; partial OK)
- Overpayment → `loan.credit_balance` (not 4950)
- Single consolidated `account.move` per payment
- See ACCOUNTING_SPEC.md Section 7 for full code structure

### Base Module Accounting Gaps (what must be overridden)
- Single `receivable_account_id` instead of 4110+262 split
- No `accrued_interest_account_id` (4960) — interest not accrued separately
- Penalty and fee both credited to `interest_income_account_id` (wrong accounts)
- Payment FIFO order wrong: base does Interest → Penalty → Fee → Principal
- Wizard date readonly — no daily interest calc to payment date
- No `exclude_penalty` checkbox / no custom penalty amount
- No LT/ST reclassification
- No provision for loan losses
- **4961 NOT used** — base module penalty cron replaced by informational-only calc

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

## LOGOS CURRENCY
- **EUR (Euro)** — active, company currency
- **BGN** — inactive (Bulgaria joins Eurozone 2026)
- All loan amounts displayed and entered in **€**
- Fixed rate 1.95583 (historical reference only — EUR is primary)

## BULGARIAN COMPLIANCE REQUIREMENTS
- ГПР mandatory on every contract (max 50%)
- ЕИК for companies (9 or 13 digits with checksum)
- EGN for individuals (10 digits with checksum)
- BGN/EUR dual currency (fixed rate 1.95583)
- Sequential invoice numbering

## ANACREDIT INTEGRATION (Phase 8 — post go-live)

> **Reference:** `AnaCredit_CLAUDE.md` — full spec of the standalone generator.
> **Standalone script:** `C:\BNB_Reports\Data_base\Anacredit Monthly\anacredit_generator_v3.0.py` (v3.1, working)

### Strategy
```
Odoo customer.loan → Export Wizard → CUCR_enhanced.csv → anacredit_generator_v3.0.py → 10 BNB tables → BNB upload
```
The generator script is **already operational in production**. Odoo integration adds automation only.

### Odoo field → CUCR_enhanced.csv mapping

| CUCR Column | Odoo Source | Notes |
|---|---|---|
| `CUCR_DATE` | Report month (wizard input) | YYYYMMDD |
| `CUCR_CRED` | `customer.loan.name` | Contract number |
| `CUCR_BAE` | `res.config.settings.anacredit_agent_id` | e.g. BGR00441 |
| `CUCR_BORR` | `customer_id.company_registry` / `personal_number` | EIK or EGN |
| `CUCR_REC` | Computed from loan status | 5=active, 6=closed, 7=restructured, 8=new, 9=written-off |
| `CUCR_EXP_NOM` | Computed from DPD + status | 70=performing, 73=NPL |
| `CRED_DAT1` | `approval_date` | Credit initiation date |
| `CRED_DAT2` / `DATF` | `end_date` | Maturity dates |
| `CUCR_SUMA` | `loan_amount` | Disbursed amount |
| `CUCR_TOT_BALANS` | Sum of remaining principal from schedule | |
| `CUCR_INTR` | `interest_rate` | 6 decimal places |
| `CUCR_PRINC_OVER` | Overdue principal from `loan_lines_ids` | |
| `CUCR_OVER_INTER` | Overdue interest from `loan_lines_ids` | |
| `CUCR_JUD_DUES` | New field `anacredit_jud_dues` on loan | Default 0 |
| `CUCR_TOT_OFFBAL` | New field `anacredit_tot_offbal` on loan | Default 0 |
| `BORR_TYPE` | `customer_id.is_company` → 1/2/3 | 1=EGN, 2=EIK, 3=BULSTAT |
| `CRED_SPEC` | `loan_type_id.anacredit_cred_spec` | New field on loan type |
| `CRED_GRACE_PER` | Computed from `grace_period` | 90=fixed, 92=interest-only, 91=balloon |
| `CRED_CO_BORR` | `codebtor_line_ids[0].partner_id.company_registry` | First codebtor EIK/EGN |
| `DAYS_PAST_DUE` | Max days overdue from schedule lines | |

### CUCR_EXP_NOM mapping (BNB codes)
| Code | Meaning | Condition |
|------|---------|-----------|
| 70 | Performing | DPD < 30 |
| 71 | Watch list | DPD 30–60 |
| 72 | Substandard | DPD 60–90 |
| 73 | Doubtful | DPD 90–180 |
| 74 | Loss | DPD > 180 |

### New config fields needed (GROUP AC-1)
- `res.config.settings.anacredit_agent_id` — Char, BNB reporting agent code (BGR00441 etc.)
- `res.config.settings.anacredit_version` — Char, default '0.9'
- `customer.loan.type.anacredit_cred_spec` — Char, instrument type code (102/110/111 etc.)
- `customer.loan.anacredit_jud_dues` — Monetary, judgment dues
- `customer.loan.anacredit_tot_offbal` — Monetary, off-balance sheet amount

## CRITICAL BUSINESS RULES

### Installment Dates — IMMUTABLE after disbursement

Once `customer.loan.status == 'in_progress'`:
- `customer.loan.lines.emi_date` is **permanently readonly**
- **No wizard, no admin, no cron, no script, no system upgrade** may change an existing `emi_date`
- The date in the signed contract = the date in the database. Always.

**Legal basis:** Loan contract obligations, AnaCredit DPD reporting, interest accrual trigger, penalty start calculation, journal entry dates.

**Technical enforcement** — add `_write()` override to `CustomerLoanLineAccrualBG` (or a dedicated model mixin):

```python
def _write(self, vals):
    if 'emi_date' in vals:
        if not self.env.context.get('allow_annex_change'):
            loans = self.mapped('customer_loan_id')
            if any(l.status == 'in_progress' for l in loans):
                raise UserError(
                    "Датата на вноска не може да бъде променяна "
                    "след активиране на кредита.")
        else:
            # allow_annex_change=True requires manager permission
            if not self.env.user.has_group(
                    'tk_loan_management.department_manager'):
                raise UserError(
                    "Само мениджър може да променя дата по анекс.")
    return super()._write(vals)
```

**Exception flow (signed annex — анекс):**
- Requires `context={'allow_annex_change': True}`
- Requires `group_loan_manager` permission
- Mandatory reason field + audit log entry
- This is a manual, human-authorised operation — never automated

**Exceptions that create NEW lines (old lines frozen):**
- Restructure (`action_recalculate_installment()`) — unlinks future lines, creates new schedule
- Decrease-term wizard — unlinks future lines, creates new schedule
- Pre-closure — cancels future lines entirely

### Holiday-Aware Date Generation — NEW loans only

Holidays affect **ONLY** initial schedule generation (before disbursement):

1. System calculates installment date normally (e.g. every 20th of month)
2. If date falls on Bulgarian public holiday or weekend → system **suggests** next business day
3. Loan officer **reviews and confirms** (human must confirm — system never auto-applies)
4. Officer may override if needed
5. Date is **locked** after disbursement — immutable from that point

```python
def _next_business_day(self, d):
    """Suggest next business day if holiday/weekend. Pre-disbursement only."""
    holidays = self._get_bg_holidays(d.year)
    while d.weekday() >= 5 or d in holidays:
        d += timedelta(days=1)
    return d

def _get_bg_holidays(self, year):
    """Query resource.calendar.leaves for company calendar."""
    leaves = self.env['resource.calendar.leaves'].search([
        ('calendar_id', '=', self.env.company.resource_calendar_id.id),
        ('date_from', '>=', f'{year}-01-01'),
        ('date_from', '<=', f'{year}-12-31'),
        ('time_type', '=', 'leave'),
    ])
    return {fields.Date.from_string(l.date_from) for l in leaves}
```

**NEVER retroactively adjust existing `emi_date` for holidays.**
Penalty calculation and interest accrual always use **calendar days** from contract date — holiday awareness is a scheduling courtesy, not an accounting rule.

### Holiday Coverage — setup_generic.py

`setup_generic.py` populates `resource.calendar.leaves` for years 2026–2035:
- **Fixed holidays** (10 days × 10 years): Jan 1, Mar 3, May 1, May 6, May 24, Sep 6, Sep 22, Dec 24, Dec 25, Dec 26
- **Weekend compensation** (КТ чл.154 ал.2): auto-calculated per year
- **Orthodox Easter** (4 days × 10 years): auto-calculated via algorithm
- **Special one-off**: Jan 2 2026 — "Еднократен почивен — въвеждане EUR"

Annual coverage check cron (`_cron_holiday_coverage_check`) runs December 1st each year.
If max covered year − current year ≤ 2: sends notification to admin via `mail.message`.

## DEVELOPMENT RULES
- Always use `TEST_MODE = True` by default in scripts
- Field labels must be in Bulgarian
- Never hardcode company-specific data — use `res.company` or `ir.config_parameter`
- All company info must come from settings, not baked into templates
- Prefer editing existing files over creating new ones
- Never modify files inside `tk_loan_management/`
- **Before any accounting code: read `ACCOUNTING_SPEC.md` first**
- **Never hardcode `penalty_rate_annual`, `penalty_divisor`, `penalty_grace_days`** — always read from `res.config.settings`
- All JEs must carry: `partner_id`, `loan_id` ref, `ref` (human-readable), `journal_id`
- **`emi_date` is immutable after disbursement** — never change in code without `allow_annex_change` context + manager group
