# Investigation Summary: tk_loan_management Module

Date: 2025-02-24
Module: `tk_loan_management` v1.0.6 by TechKhedut
Odoo Version: 19

---

## 1. Module Structure

### File Layout
```
tk_loan_management/
├── models/
│   ├── customer_loan.py              (2512 lines — main loan + 7 sub-models)
│   ├── customer_loan_type.py         (152 lines — loan product config)
│   ├── customer_loan_res_partner.py  (267 lines — partner extensions)
│   └── customer_loan_account_move.py (~40 lines — journal entry override)
├── views/
│   ├── customer_loan_views.xml       (loan form/tree/kanban)
│   └── res_partner.xml               (partner form extension)
├── reports/
│   └── loan_contract.xml             (contract PDF template, ~1400 lines)
├── i18n/
│   └── bg.po                         (Bulgarian translation, ~95% coverage)
├── data/                             (sequences, cron jobs, mail templates)
└── security/                         (access rules)
```

### All 14 Models

| # | Model | Location | Purpose |
|---|-------|----------|---------|
| 1 | `customer.loan` | customer_loan.py:1 | Main loan record |
| 2 | `customer.loan.lines` | customer_loan.py:2042 | Installment schedule |
| 3 | `customer.loan.document.lines` | customer_loan.py:2167 | Uploaded documents |
| 4 | `customer.collateral.lines` | customer_loan.py:2272 | Collateral records |
| 5 | `customer.loan.installment.penalty.lines` | customer_loan.py:2315 | Penalty tracking |
| 6 | `customer.loan.request.document` | customer_loan.py:2354 | Document requests |
| 7 | `customer.loan.request.collateral` | customer_loan.py:2380 | Collateral requests |
| 8 | `customer.loan.sanction.latter` | customer_loan.py:2413 | Sanction letters |
| 9 | `customer.loan.type` | customer_loan_type.py:8 | Loan product config |
| 10 | `customer.loan.type.term.lines` | customer_loan_type.py:97 | Rate overrides by term |
| 11 | `loan.type.document.lines` | customer_loan_type.py:133 | Required docs per type |
| 12 | `customer.income.line` | customer_loan_res_partner.py:223 | Partner income entries |
| 13 | `customer.expense.line` | customer_loan_res_partner.py:235 | Partner expense entries |
| 14 | `family.info` / `labour.relation` | customer_loan_res_partner.py:251,260 | Lookup tables |

---

## 2. Partner Fields (res.partner Extension)

### Fields Added by Module
```
personal_number     Char        Bulgarian EGN (10 digits, validated)
id_card             Char        ID card number (9 digits or 2 letters + 7 digits)
validity_type       Selection   '10_years' / 'indefinite'
date_of_issuing     Date        ID card issue date
date_of_validity    Date        Computed from issue date + 10 years
issued_by           Char        Issuing authority

is_loan_borrower    Boolean     Role: Loan Borrower
is_person_of_contact Boolean    Role: Person of Contact
is_codebtor         Boolean     Role: Codebtor

codebtor_ids        M2M(res.partner)  Partner's codebtors (partner-to-partner)

family_info_id      M2O(family.info)
no_of_children      Integer
date_of_salary_to   Selection   '10' / '20' / '30'

labour_relation_id  M2O(labour.relation)
employer            Char
ep_street/street2/city/zip/state_id/country_id   Employer address

income_line_ids     O2M(customer.income.line)
expense_line_ids    O2M(customer.expense.line)
total_income        Monetary (computed)
total_expense       Monetary (computed)

bank_account        Char
payment_method      Selection   'cash' / 'bank_transfer'
notes               Html
```

### EGN Validation Logic
Location: `customer_loan_res_partner.py:136-204`
- Checks exactly 10 digits
- Extracts birth date (handles 19th/20th/21st century encoding via month offset)
- Validates calendar date
- Checksum: weights `[2, 4, 8, 5, 10, 9, 7, 3, 6]`, mod 11 (10→0)

---

## 3. Loan Fields (customer.loan)

### Status Workflow
```
draft → confirm → dept_approval → confirmation → disbursement → in_progress
                                                                    ↓
                                                     closure / pre_closure / settlement
Also: rejected, cancel (from various states)
```

### Key Field Groups

**Customer:** `customer_id`, `phone`, `email`, `app_date`

**Requested:** `requested_loan_amount`, `requested_start_date`, `requested_installment_type`, `requested_term`

**Approved:** `approval_date`, `loan_amount`, `start_date`, `term`, `installment_type`, `installment_amount`, `interest_rate`

**Bank (customer):** `cst_bank_name`, `cst_bank_account_number`, `cst_bank_branch_code`, `cst_bank_swift_bic_code`

**Accounting:** `receivable_account_id`, `bank_cash_account`, `interest_income_account_id`, `journal_item_id` (disbursement), `repayment_journal_item_id`, `journal_entry_id`

**Fees:** `is_fee`, `fee_amount`, `is_initial_fee`, `initial_fee_amount`, `is_processing_fee`, `processing_fee_type`, `processing_fee_amount`, `processing_fee_percentage`

**Penalty:** `is_penalty`, `penalty_type` (fixed/percentage), `penalty_amount`, `penalty_percentage`

**Grace Period:** `is_grace_period`, `grace_period` (months)

**Installments:** `loan_lines_ids` (O2M to `customer.loan.lines`), `installment_start_date`, `end_date` (computed)

**Settlement:** `settlement_date`, `settlement_amount`, `forgiven_debt`, `settlement_journal_entry_id`

### Loan Line Fields (`customer.loan.lines`)
```
customer_loan_id      M2O(customer.loan)
installments_no       Char        "Installment No."
emi_date              Date        Installment due date
installment_amount    Monetary    Principal portion
interest_amount       Monetary    Interest portion
total_installment_amount Monetary Principal + Interest
fee_amount            Monetary    Per-installment fee
total_paid_amount     Monetary
remaining_amount      Monetary
principal_balance     Monetary
invoice_id            M2O(account.move)     Payment invoice
journal_entry_id      M2O(account.move)     Repayment journal entry
penalty_invoice_id    M2O(account.move)
installment_od_count  Integer               Overdue counter
```

---

## 4. Financial Calculations

### What EXISTS — EMI/PMT Formula
Location: `customer_loan.py:1343-1361`

```python
def _calculate_emi(self, loan_amount, interest_rate, term, installment_type):
    periods_per_year = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
    periods = periods_per_year.get(installment_type, 12)
    rate_per_period = interest_rate / periods / 100

    if rate_per_period != 0:
        emi = (loan_amount * rate_per_period * (1 + rate_per_period) ** term) / (
                (1 + rate_per_period) ** term - 1)
    else:
        emi = loan_amount / term

    total_amount = emi * term
    return emi, total_amount
```

Standard annuity formula. Annual rate divided by periods per year.

### What is MISSING
- **APR / ГПР (Годишен Процент на Разходите)** — not calculated anywhere
- **IRR / XIRR** — no internal rate of return calculation
- **Total cost of credit** — not computed
- **No numpy, scipy, or financial libraries** imported
- No validation against the Bulgarian legal maximum ГПР (50%)

### Interest Rate Resolution
1. If `interest_rate` already set on loan → use it
2. Else if loan type has `term_lines_ids` → find matching `(duration >= term, installment_type)` line
3. Else if loan type has `is_interest=True` → use loan type's base `interest_rate`
4. Otherwise → 0

---

## 5. Accounting Automation

### Disbursement Journal Entry
Created by `action_disburse_loan()` (line 1683):
```
Debit:  receivable_account_id    (loan_amount)    partner=customer
Credit: bank_cash_account        (loan_amount)    partner=company
```
If processing fee deducted from disbursement, adds extra lines.

### Installment Repayment Journal Entry
Created by `action_create_journal_entry()` on loan lines (line 2120):
```
Debit:  bank_cash_account           (total_installment_amount)  partner=company
Credit: receivable_account_id       (installment_amount)        partner=customer
Credit: interest_income_account_id  (interest portion)          partner=customer
```

### Journal Entry Posting
`action_post()` override in `customer_loan_account_move.py`:
- Calls `super().action_post()`
- If `is_disbursement=True`, sends disbursement confirmation email
- Sets `entry_post_date = today`

---

## 6. Contract Template Issues

### Location
`reports/loan_contract.xml` (~1400 lines of Bulgarian legal text)

### Hardcoded Company Info
Lines 28-40 contain hardcoded lender details:
- Company name: Explicitly names the lending company
- ЕИК: `200735614` hardcoded
- Address: Specific Sofia address hardcoded
- Representative name: Hardcoded

### Guarantor Section
Lines 62-76: "Поръчител" (Guarantor) section has **static placeholder text**:
```
ЕИК _______________
ЕГН _____________
лична карта № ___________
```
Not populated from any field — completely manual fill-in.

### Contract Terms
Full Bulgarian legal contract with ~30 articles covering:
- Loan parameters (from loan record fields — amount, term, rate)
- Repayment schedule (from loan lines)
- Penalties and default terms
- Early repayment rights
- Guarantor obligations
- Data protection (GDPR)
- Dispute resolution

---

## 7. Codebtor Implementation — Gap Analysis

### What Exists
On `res.partner`:
- `is_codebtor` Boolean — role flag checkbox
- `codebtor_ids` Many2many(res.partner) — partner-to-partner link

### What's Wrong
1. **Not linked to loan** — `customer.loan` has zero references to codebtor
2. **No domain filter** — `codebtor_ids` in the view has no `domain="[('is_codebtor', '=', True)]"`
3. **No guarantor role** — only `is_codebtor`, but contract template uses "Поръчител" (guarantor)
4. **Partner-level only** — codebtors are a property of the person, not per-loan
5. **Contract uses static text** — guarantor details are `___________` placeholders

### What Should Exist
- `guarantor_ids` / `codebtor_ids` Many2many on `customer.loan`
- Domain enforcement requiring `is_guarantor=True` / `is_codebtor=True`
- Contract template dynamically populated from loan's guarantor records

---

## 8. Company vs Individual Borrower — Gap Analysis

### What Exists
The "Other Info" tab in `res_partner.xml` shows ALL fields to ALL partners:
- `personal_number` (EGN) — **required="1"** in view, no `invisible` condition
- `id_card` — **required="1"** in view, no `invisible` condition
- `date_of_issuing` — **required="1"**, no visibility condition
- `family_info_id`, `no_of_children` — shown to companies too
- `employer`, `labour_relation_id` — shown to companies too

### What's Missing
| Expected | Status |
|----------|--------|
| `invisible="is_company"` on EGN/ID card fields | **Missing** |
| ЕИК field for companies | **Missing** — no field defined |
| БУЛСТАТ field | **Missing** |
| МОЛ (Материално Отговорно Лице) for companies | **Missing** |
| Company registry / Търговски регистър | **Missing** |
| Different validation for company vs individual | **Missing** — always validates as EGN |
| Domain on `customer_id` filtering by type | **Missing** |

### EGN Validation
`_check_personal_number()` at line 83 always runs EGN validation. A company partner would fail unless its "EGN" accidentally passes the 10-digit checksum. No way to skip for companies.

---

## 9. Cron Jobs

### 1. Loan Reminders
- Sends email notifications before installment due date
- Uses mail template `loan_installment_reminder_mail_template`
- Configurable days-before via system parameter

### 2. Penalty Application
- Searches for overdue installments (past `emi_date`, no `journal_entry_id`)
- Applies penalty based on loan's `penalty_type` (fixed amount or percentage)
- Creates penalty lines in `customer.loan.installment.penalty.lines`

### 3. Compound Interest
- Calculates compound interest on overdue amounts
- Updates penalty amounts over time

---

## 10. Loan Type Configuration

### Fields on `customer.loan.type`
```
product_id              M2O(product.product)    Delegated inheritance
is_interest             Boolean                 Toggle interest calculation
interest_rate           Float                   Base rate
term_lines_ids          O2M                     Rate overrides by term bracket
is_fee                  Boolean                 Per-installment fee
fee_amount              Float                   Fee percentage
is_initial_fee          Boolean                 One-time upfront fee
initial_fee_amount      Float                   Upfront fee amount
loan_doc_ids            O2M                     Required document types
terms_and_conditions    Html                    From template
repayment_terms         Html                    From template
```

### Term Lines (`customer.loan.type.term.lines`)
Each line: `duration` (max installments), `interest_rate`, `installment_type`
- Constrained: no duplicate (duration, installment_type) pairs
- Rate must be >= 0

### What's Missing from Loan Type
- Min/max loan amount
- Min/max term
- Allowed installment types
- ГПР cap per product
- Currency restrictions

---

## 11. Bulgarian-Specific Features Found

### Translation
- `bg.po` covers ~95% of UI strings
- Number-to-words in Bulgarian implemented in `customer_loan.py` (lines 23-100+)
- Supports masculine/feminine/neuter forms

### Currency
- Uses `res.currency` — BGN expected
- No EUR dual-currency handling built in
- No fixed BGN/EUR rate (1.95583) implementation

### Date Handling
- Holiday-aware installment dates via `_get_public_holiday_dates()`
- Skips Sundays via `_get_valid_installment_date()` (adjusts backward)
- Uses `dateutil.relativedelta` for month arithmetic

---

## 12. Sequence / Naming
- Loan name: sequence code `customer.loan.sequence`, prefix `CSL/`
- Sanction letter: sequence code `customer.loan.sanction.letter.sequence`
- Document requests: sequence code `customer.loan.req.doc.sequence`
- Collateral requests: sequence code `customer.loan.req.col.doc.sequence`

---

## 13. Summary of Gaps for `tk_loan_management_bg`

| # | Gap | Severity | Phase |
|---|-----|----------|-------|
| 1 | No company borrower support (ЕИК/МОЛ) | **Critical** — client has mostly company borrowers | Phase 2 ✅ |
| 2 | EGN required for all partners | **Critical** — blocks company partner creation | Phase 2 ✅ |
| 3 | No ГПР calculation | **Critical** — Bulgarian legal requirement | Phase 4 ✅ |
| 4 | Contract hardcoded to specific company | **High** — must be dynamic | Phase 5 ✅ |
| 5 | Guarantor not linked to loan | **High** — contract references guarantor | Phase 3 ✅ |
| 6 | Codebtor role not enforced | **Medium** — any partner can be added | Phase 3 ✅ |
| 7 | No AnaCredit fields | **Medium** — BNB reporting needed eventually | Phase 8 |
| 8 | Installments not editable | **Medium** — can't correct errors | Postponed |
| 9 | No min/max on loan type | **Low** — nice to have | Phase 4 |
| 10 | No EUR dual currency | **Low** — most loans in BGN | Future |

---

## 14. Payment & Accounting Deep-Dive (2026-03-12)

Analysis of: `customer_loan.py`, `wizard/loan_payment.py`, `data/ir_cron.xml`
against 9 operational questions from Logos client requirements.

---

### 14.1 CASH DISBURSEMENT
**Status: ✅ DONE**
**Found in:** `customer_loan.py:201-204`, `customer_loan_views.xml:807-810`, `customer_loan.py:1994-2062`

```python
disbursement_payment_type = fields.Selection([
    ('cash', 'Cash'),
    ('bank_transfer', 'Bank Transfer')
])
```
Radio button widget in view. Disbursement JE posts:
- Debit: `receivable_account_id` (loan receivable)
- Credit: `bank_cash_account` (whichever account is configured on the loan)

**Residual gap:** No separate petty cash account field — both cash and bank variants use the same `bank_cash_account` Many2one. The selection affects the label but not the account used.

---

### 14.2 FEE SEPARATION IN JOURNALS
**Status: ⚠️ PARTIAL**
**Found in:** `customer_loan.py:110-114, 205-219`, `wizard/loan_payment.py:198-226`

Fees ARE a separate round in payment allocation (Round 3: fee, after interest, before principal). Each fee payment creates a separate journal line with `is_fee = True` marker.

**Gap:** No `fee_income_account_id` field. Fees are credited to `interest_income_account_id` — the same account as interest. Impossible to separate fee income from interest income at the account/GL level. Affects Bulgarian chart of accounts compliance (721 vs 728/similar).

---

### 14.3 PENALTY JOURNAL ENTRY TIMING
**Status: ✅ DONE (accrual-based daily)**
**Found in:** `data/ir_cron.xml:15-23`, `customer_loan.py:953-1015`

Cron trigger: `_cron_installment_due_penalty()` — runs **every day** automatically.

```python
# JE structure (lines 982-1005):
# Debit:  bank_cash_account          (penalty amount)
# Credit: interest_income_account_id (penalty income — same as interest account)
```

Penalty JE is created once per overdue installment, the day after `emi_date`, independent of payment.

**Note:** Penalty is credited to `interest_income_account_id`, not a dedicated penalty income account — same gap as fees (see 14.2).

---

### 14.4 PENALTY EXCLUDE CHECKBOX
**Status: ❌ MISSING**
**Found in:** Nothing. Searched `exclude_penalty`, `waive_penalty`, `skip_penalty`, `penalty_waived` — zero results in entire codebase.

**Gap:** Full feature missing. No Boolean or field of any kind to waive/exclude penalty on a specific installment or payment. Once `is_penalty = True` on the loan, all overdue installments accrue penalty automatically. No override mechanism.

---

### 14.5 CALCULATE DUE UP TO SELECTED DATE
**Status: ⚠️ PARTIAL**
**Found in:** `wizard/loan_payment.py:34, 42-60`, `wizard/loan_payment_view.xml:15`

A `date` field exists in the wizard and `_compute_remain_amount` uses it — collects all installments where `emi_date <= date`. The logic skeleton is in place.

**BUT:** The date field is `readonly="1"` in the view — user cannot change it. Always defaults to `fields.Date.today()`.

**Gaps:**
1. Date field hardcoded as readonly — **no user-selectable date**
2. **No daily interest** — interest is fixed per installment; no pro-rata calculation for days between due date and payment date
3. **No daily penalty** — penalty is cron-based; not recalculated dynamically on the wizard's payment date

---

### 14.6 DECREASE INSTALLMENT RESTRUCTURE (keep term, lower EMI)
**Status: ✅ DONE**
**Found in:** `customer_loan.py:1619-1723`
**Function:** `action_recalculate_installment()`

Takes `credit_balance` (overpayment), subtracts from remaining principal, recalculates EMI for the **same number of remaining installments** → lower installment amount. Unlinks old unpaid installments, creates new schedule, triggers email notification.

---

### 14.7 DECREASE TERM RESTRUCTURE (keep EMI, shorten term)
**Status: ❌ MISSING**
**Found in:** Nothing. Searched `decrease_term`, `shorten_term`, `same_installment`, `keep_installment` — zero results.

**Gap:** Full feature missing. `action_recalculate_installment()` only does the reverse (keeps term, reduces EMI). No "keep same installment, shorten term" restructure option exists.

---

### 14.8 OVERPAYMENT HANDLING
**Status: ✅ DONE (manual trigger)**
**Found in:** `customer_loan.py:321`, `wizard/loan_payment.py:259-260`, `customer_loan_views.xml:711-715`

```python
credit_balance = fields.Monetary()  # on customer.loan
# After all payment rounds, leftover:
if amount > 0:
    loan_id.credit_balance = amount
```

Stored in `credit_balance`, displayed in loan view when > 0.

**Residual gap:** Not automatically applied to the next installment. User must manually trigger `action_recalculate_installment()` to apply the credit balance. Acceptable for Logos use case.

---

### 14.9 BULGARIAN ACCOUNTS (411, 228, 721, 724)
**Status: ❌ MISSING (account codes) / ⚠️ PARTIAL (account fields)**
**Found in:** Zero matches for account codes `411`, `228`, `721`, `724` anywhere in codebase.

Account fields that exist on `customer.loan`:

| Field | Account role | Used for |
|-------|-------------|---------|
| `receivable_account_id` | 411 equivalent | Loan principal receivable |
| `bank_cash_account` | Cash/Bank | Disbursement credit / repayment debit |
| `interest_income_account_id` | 721 equivalent | Interest income — **AND penalty AND fee** |
| `journal_item_id` | — | Disbursement journal |
| `repayment_journal_item_id` | — | Repayment journal |

**Three problems:**
1. **No default accounts** — must be manually selected on every loan; no defaults on loan type or company settings
2. **No `penalty_income_account_id`** — penalty credited to `interest_income_account_id`
3. **No `fee_income_account_id`** — fees credited to `interest_income_account_id`

For Bulgarian compliance need at minimum:
- `receivable_account_id` → 411
- `interest_income_account_id` → 721
- `penalty_income_account_id` → 724 (separate field needed)
- `fee_income_account_id` → 728 or similar (separate field needed)
- Defaults configurable on `customer.loan.type` (not per-loan)

---

### 14.10 Summary Table

| # | Item | Status | Fixable in `tk_loan_management_bg` |
|---|------|--------|-------------------------------------|
| 1 | Cash disbursement | ✅ | n/a |
| 2 | Fee separate account | ⚠️ | ✅ Add `fee_income_account_id` field + loan type default |
| 3 | Penalty timing (daily accrual) | ✅ | n/a |
| 4 | Penalty exclude/waive checkbox | ❌ | ✅ Add `waive_penalty` Boolean on installment line |
| 5 | Calculate due to selected date | ⚠️ | ✅ Override wizard: unlock date field, add daily interest calc |
| 6 | Decrease installment restructure | ✅ | n/a |
| 7 | Decrease term restructure | ❌ | ✅ New restructure wizard option |
| 8 | Overpayment handling | ✅ | n/a (manual trigger acceptable) |
| 9 | Bulgarian account codes | ❌ | ✅ Add `penalty_income_account_id`, `fee_income_account_id`; defaults on loan type |


---

## 15. AnaCredit Integration Gap Analysis (2026-03-13)

### 15.1 What exists (standalone script — fully operational)

- **Script:** `C:\BNB_Reports\Data_base\Anacredit Monthly\anacredit_generator_v3.0.py` (v3.1)
- **Input:** `CUCR_enhanced.csv` — manually prepared from Logos's legacy software
- **Output:** 10 BNB-required CSV tables (Monthly M_FI_EA or Daily D_FI_EA)
- **Status:** Working in production. EUR transition support complete. BGN legacy credits handled per-agent.

### 15.2 What Odoo must provide (GROUP AC-1 fields)

Fields missing from `customer.loan` that are needed for CUCR_enhanced.csv export:

| CUCR Column | Status in Odoo | Action needed |
|---|---|---|
| `CUCR_DATE` | ❌ | Wizard input (report month) |
| `CUCR_CRED` | ✅ `customer.loan.name` | Direct map |
| `CUCR_BAE` | ❌ | `res.config.settings.anacredit_agent_id` |
| `CUCR_BORR` | ✅ `customer_id.company_registry` / `personal_number` | Direct map |
| `CUCR_REC` | ⚠️ | Compute from loan status (5/6/7/8/9) |
| `CUCR_EXP_NOM` | ❌ | Compute from DPD: 70/71/72/73/74 |
| `CRED_DAT1` | ✅ `approval_date` | Direct map |
| `CRED_DAT2` / `DATF` | ✅ `end_date` | Direct map |
| `CUCR_SUMA` | ✅ `loan_amount` | Direct map |
| `CUCR_TOT_BALANS` | ⚠️ | Compute from schedule lines |
| `CUCR_INTR` | ✅ `interest_rate` | Direct map |
| `CUCR_PRINC_OVER` | ⚠️ | Compute from overdue schedule lines |
| `CUCR_OVER_INTER` | ⚠️ | Compute from overdue schedule lines |
| `CUCR_JUD_DUES` | ❌ | New field `anacredit_jud_dues` |
| `CUCR_TOT_OFFBAL` | ❌ | New field `anacredit_tot_offbal` |
| `BORR_TYPE` | ✅ `customer_id.is_company` | Map: False→1, True→2 |
| `CRED_SPEC` | ❌ | New field on `customer.loan.type` |
| `CRED_GRACE_PER` | ⚠️ | Map from loan `grace_period` type |
| `CRED_CO_BORR` | ✅ `codebtor_line_ids[0]` | Extract EIK/EGN of first codebtor |
| `DAYS_PAST_DUE` | ⚠️ | Compute from max overdue installment |

**Legend:** ✅ exists and maps directly | ⚠️ needs computed logic | ❌ new field required

### 15.3 New fields required (minimal additions)

On `customer.loan`:
- `anacredit_jud_dues` Monetary (default 0) — judgment dues
- `anacredit_tot_offbal` Monetary (default 0) — off-balance sheet amount

On `customer.loan.type`:
- `anacredit_cred_spec` Char — BNB instrument type code (102/110/111/111G/113/114/115/117/121/124)

On `res.config.settings`:
- `anacredit_agent_id` Char — BNB reporting agent code (BGR00441 etc.)
- `anacredit_version` Char — default '0.9'

### 15.4 Computed logic required (GROUP AC-2 export wizard)

```python
# CUCR_REC from loan status:
status_to_rec = {
    'disbursement': '8',   # New
    'in_progress':  '5',   # Active
    'closure':      '6',   # Closing
    'settlement':   '6',   # Closing
    # restructured (detect from recalculate history): '7'
    # written-off: '9'
}

# CUCR_EXP_NOM from DPD:
def exp_nom(days_past_due):
    if days_past_due < 30:  return 70  # Performing
    if days_past_due < 60:  return 71  # Watch list
    if days_past_due < 90:  return 72  # Substandard
    if days_past_due < 180: return 73  # Doubtful
    return 74                           # Loss

# CRED_GRACE_PER from loan type:
grace_map = {'fixed': '90', 'interest_only': '92', 'balloon': '91'}
```

### 15.5 Workflow (unchanged — generator script stays standalone)

```
1. Monthly: run Odoo export wizard → downloads CUCR_enhanced.csv
2. Copy to: C:\BNB_Reports\Data_base\Anacredit Monthly\Input_Anacredit\
3. Run: python anacredit_generator_v3.0.py --report-type monthly
4. Upload 10 output CSVs to BNB portal
```


---

## Section 16: Payment FIFO Order Decision (2026-03-14)

### Finding 2 — Corrected Payment Algorithm

**Previous understanding (wrong):** Per-installment waterfall — fully clear each installment
(Penalty→Interest→Fee→Principal) before moving to the next installment.

**Correct approach for Logos:** Global 4-round sweep across ALL installments.

### Why global sweep is correct

A per-installment waterfall means a partial payment that covers penalty and interest of
installment #1, but not its principal, would be blocked from clearing penalty on installment
#2. This is operationally wrong — ЗПК Art. 35 mandates priority ORDER (penalty first,
principal last), not per-installment isolation.

The global sweep respects ЗПК Art. 35 priority AND allows partial payments to clear
accumulated penalty and interest across multiple overdue installments before touching any
principal. This matches how Bulgarian NFIs operate in practice.

### Algorithm (Decision: 2026-03-14)

```
remaining = amount_paid
installments = all unpaid, sorted by emi_date ASC

Round 1 — ALL penalties (all installments, oldest first):
    for each inst: pay = min(penalty_due, remaining) → DR 5031 / CR 7230

Round 2 — ALL fees (all installments, oldest first):
    for each inst: pay = min(fee_due, remaining) → DR 5031 / CR 4113

Round 3 — ALL interest (all installments, oldest first):
    for each inst: pay = min(interest_due, remaining) → DR 5031 / CR 4960

Round 4 — Principal FIFO (oldest first, partial OK):
    for each inst: pay = min(principal_due, remaining) → DR 5031 / CR 4112 or 4110

Overpayment: loan.credit_balance += remaining
```

### Impact on GROUP E (Payment Wizard)

- `wizard/loan_payment_bg.py` must implement this 4-round algorithm
- Single consolidated `account.move` created per payment with all line items
- Per-installment `paid_*` fields updated after each round
- `penalty_accrued_informational` reset to zero after penalty payment
- Principal account chosen per-installment: 4112 if `inst.status == 'overdue'`, else 4110

### Files updated

- `ACCOUNTING_SPEC.md`: Section 7 fully rewritten with global sweep algorithm, code structure,
  example JEs, and wizard penalty options table

---

## Section 17: TechKhedut Integrity Check (2026-03-15)

### Purpose
Verify that `tk_loan_management/` (OPL-1, TechKhedut) has not been modified by VitoshaBG.
Run before go-live as evidence of license compliance.

### Checks performed

| Check | Command | Result |
|-------|---------|--------|
| Diff against HEAD | `git diff HEAD -- tk_loan_management/` | **Empty** — no changes |
| Commit log | `git log --oneline -- tk_loan_management/` | 2 commits (see below) |
| Working tree | `git status tk_loan_management/` | `nothing to commit, working tree clean` |
| Content scan | `grep -r "VitoshaBG\|tk_loan_management_bg\|Logos" tk_loan_management/ --include="*.py" --include="*.xml"` | **Zero matches** |

### Git log explanation

```
092e0e1  techkhedut@gmail.com  [IMP] Loan Management       ← TechKhedut delivery
4be8bfa  g.penev@gmail.com     Phase 2: Partner fixes…     ← our commit
```

The Phase 2 commit appears in `git log -- tk_loan_management/` because that is the commit
where `tk_loan_management/` was **first added to git** (all `+` insertions, zero edits).
Every file in that commit shows `Bin 0 -> N bytes` or `N +` lines — no deletions, no
modifications. The `git diff HEAD -- tk_loan_management/` being empty confirms the files
are unchanged from that point.

### Result: CLEAN ✅

- `git diff` → empty
- `grep VitoshaBG/Logos` → zero matches
- All TechKhedut files byte-for-byte identical to `092e0e1` delivery
- OPL-1 license compliance: **intact**
- Our code: 100% in `tk_loan_management_bg` via Odoo `_inherit`

---

## Section 18: Core Business Rules (2026-03-15)

### 18.1 Installment Date Immutability

**Rule:** `customer.loan.lines.emi_date` is permanently immutable once `customer.loan.status = 'in_progress'`.

**Legal basis:**
- Loan contract signed by client references specific installment dates
- AnaCredit DPD (Days Past Due) is counted from the contract `emi_date` — any retroactive change would falsify regulatory reporting
- Bulgarian consumer credit law (ЗПК) anchors interest and penalty calculations to the agreed repayment schedule

**Operational basis:**
- GROUP C interest accrual cron fires on exact `emi_date`
- GROUP D penalty starts from `emi_date + grace_days`
- GROUP F overdue reclassification triggers from `emi_date < today`
- All JE `date` fields reference `emi_date`

**Technical enforcement:**
- `_write()` override on `customer.loan.lines` blocks `emi_date` changes when `loan.status = 'in_progress'`
- Exception: `context={'allow_annex_change': True}` + `group_loan_manager` required (signed annex scenario)
- Restructure/pre-closure wizards do **not** change `emi_date` — they unlink future lines and create new ones

**What is NOT an exception:**
- Holiday detection — never retroactively adjusts existing dates
- Weekend detection — same
- Any cron, wizard, or script — same

### 18.2 Holiday-Aware Date Generation (new loans only)

**Rule:** Holidays apply only at initial schedule generation (pre-disbursement). System **suggests** a business day adjustment; loan officer **confirms**. After disbursement: immutable.

**Holiday data:** `resource.calendar.leaves`, populated by `setup_generic.py`.
- Coverage: 2026–2035 (10 years)
- Fixed Bulgarian public holidays: 10 days × 10 years
- Orthodox Easter: auto-calculated
- Weekend compensation: КТ чл.154 ал.2, auto-calculated per year
- Special 2026: Jan 2 — "Еднократен почивен — въвеждане EUR"

**Annual coverage check:** Cron runs December 1st. If `max_covered_year − current_year ≤ 2` → admin notification via `mail.message`.

**Not affected by holidays:**
- Any in-progress loan (immutable dates)
- Penalty and interest calculations (always calendar days from contract date)
- Any reclassification or accrual cron

### 18.3 Summary table

| Scenario | Holiday applies? | `emi_date` changeable? |
|----------|-----------------|----------------------|
| New loan, pre-disbursement, schedule generation | ✅ Yes — suggest only | ✅ Officer can edit |
| Loan in `draft` / `confirm` before disburse | ✅ Yes — suggest only | ✅ Editable |
| Loan `in_progress` — any cron | ❌ No | ❌ Immutable |
| Loan `in_progress` — payment wizard | ❌ No | ❌ Immutable |
| Loan `in_progress` — signed annex | ❌ No auto-adjust | ✅ Manager only, with audit log |
| Restructure / decrease-term | ❌ No | Unlinks lines, creates NEW schedule |
| Pre-closure | ❌ No | Cancels future lines |
