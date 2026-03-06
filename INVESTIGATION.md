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
| 1 | No company borrower support (ЕИК/МОЛ) | **Critical** — client has mostly company borrowers | Phase 2 |
| 2 | EGN required for all partners | **Critical** — blocks company partner creation | Phase 2 |
| 3 | No ГПР calculation | **Critical** — Bulgarian legal requirement | Phase 4 |
| 4 | Contract hardcoded to specific company | **High** — must be dynamic | Phase 5 |
| 5 | Guarantor not linked to loan | **High** — contract references guarantor | Phase 3 |
| 6 | Codebtor role not enforced | **Medium** — any partner can be added | Phase 3 |
| 7 | No AnaCredit fields | **Medium** — BNB reporting needed eventually | Phase 8 |
| 8 | Installments not editable | **Medium** — can't correct errors | Phase 3 |
| 9 | No min/max on loan type | **Low** — nice to have | Phase 4 |
| 10 | No EUR dual currency | **Low** — most loans in BGN | Future |
