# LMS Accounting Specification — Odoo 18/19 Enterprise
## Micro Loan Lending Company | Bulgarian NAS | EUR (post 01.01.2026) | НФИ

> **Document role:** This file is the authoritative accounting logic reference for the Loan Management System (LMS) Odoo module. Claude Code must read this document before writing any accounting-related Python, XML, or SQL. Cross-reference with other project files listed in Section 0.

---

## 0. Project Document Map

| File | Content | How to use |
|---|---|---|
| `ACCOUNTING_SPEC.md` | **This file** — accounts, JEs, logic | Primary reference for all accounting code |
| `loan_models.md` / `models/` | Odoo model definitions (loan.contract, loan.payment.schedule) | Field names and Many2one links |
| `payment_plan.md` | Payment plan calculation engine | Amortisation formula, EIM, schedule generation |
| `wizard_payment.md` | Payment wizard logic | Due calculation, FIFO allocation |
| `cron_jobs.md` | Scheduled actions specification | Cron triggers and payloads |
| `invoice_receipt.md` | Document generation | Receipt template, invoice auto-creation |
| `config_settings.md` | All configuration fields | Default values, validation rules |

---

## 1. Entity Classification

- **Type:** Non-bank financial institution (небанкова финансова институция — НФИ), registered under ЗКИ Art. 3a
- **Role:** LENDER. Loans issued to clients are **assets**, interest collected is **income**
- **Standard:** Bulgarian NAS (НСС). No IFRS 9 obligation below IFRS threshold
- **Currency:** EUR (Bulgaria adopted euro 01.01.2026)
- **Penalty base rate:** ECB main refinancing rate + 8 pp (Постановление № 426/2014). Current H1 2026: **10.15% p.a.** — stored in `res.config.settings.penalty_rate_annual`. Update manually when ECB changes rate

---

## 2. Chart of Accounts — Bulgarian NAS

### 2A. Asset Accounts (Balance Sheet)

| Account | Bulgarian Name | EN Name | Odoo Account Type | Notes |
|---|---|---|---|---|
| `262` | Предоставени дългосрочни заеми — клиенти | LT Loans Receivable | **Non-current Assets** | Principal remaining term > 12 months. Група 26. Analytical per client/contract |
| `4110` | Вземания по кредити — текуща вноска | ST Loans Receivable (Current) | **Current Assets** | 12-month current portion. Група 41. Reclassified monthly from 262 |
| `4112` | Просрочени вземания по кредити | Overdue Loan Principal | **Current Assets** | Overdue principal. Reclassified from 4110 when `status = overdue` |
| `4113` | Вземания за такси и комисионни | Fees Receivable | **Current Assets** | Initial fees and admin charges receivable |
| `4960` | Начислени лихви по кредити | Accrued Interest Receivable | **Current Assets** | Група 49 (Разчети по лихви). Debited at accrual, credited at payment |
| `4961` | Начислена наказателна лихва | Penalty Interest Receivable | **Current Assets** | Approach A: daily cron posts here. Cleared/reconciled at payment |
| `2991` | Провизии за загуби по кредити | Allowance for Loan Losses | **Current Assets (Contra)** | Credit balance. Reduces net portfolio on BS. Група 29 |

### 2B. Cash & Bank

| Account | Name | Odoo Type | Notes |
|---|---|---|---|
| `5030` | Разплащателна сметка — Отпускане | Bank — Disbursements | Bank and Cash. Outgoing loan payments |
| `5031` | Разплащателна сметка — Погашения | Bank — Collections | Incoming client repayments |

### 2C. Liability Accounts

| Account | Name | Odoo Type | Notes |
|---|---|---|---|
| `152` | Получени дългосрочни заеми — банки | Bank Loans Payable LT | Non-current Liabilities. Credit lines > 12 months |
| `151` | Получени краткосрочни заеми | Bank Loans Payable ST | Current Liabilities |
| `4950` | Приходи за бъдещи периоди — такси | Deferred Fee Revenue | Current Liabilities. Upfront fees not yet earned |
| `4532` | ДДС за внасяне | VAT Payable | Current Liabilities. 20% VAT on taxable items |

### 2D. Revenue — P&L (Група 7)

| Account | Name | Odoo Type | Recognition | Invoice? |
|---|---|---|---|---|
| `7210` | Приходи от лихви по кредити | Interest Income | Accrual — monthly per schedule | **NO** |
| `7220` | Приходи от такси по кредити | Initial Loan Fee Income | At disbursement (immediate) OR amortised | **YES — optional** (`invoice_initial_fees`) |
| `7230` | Приходи от наказателни лихви | Penalty Interest Income | Cash basis — at payment only | **YES — optional** (`invoice_mode`) |
| `7240` | Приходи от такси и санкции | Fee & Admin Income | At event | **YES — optional** |
| `7250` | Приходи от данъци по кредити | Loan-Related Tax Income | At disbursement | **YES — optional** (`invoice_initial_fees`) |

> **7220 + 7250 (initial fees & taxes):** These are P&L income at disbursement. Invoice generation controlled by `invoice_initial_fees` config (default: `True` for this client). The loan asset (4110/262) always equals the **full principal** — fees do NOT reduce the asset.

### 2E. Expense — P&L (Група 6)

| Account | Name | Odoo Type | Notes |
|---|---|---|---|
| `6210` | Разходи за лихви | Interest Expense on Funding | Monthly cost of bank credit lines |
| `6290` | Разходи за обезценка | Loan Loss Provision Expense | Provision charge; offset by 2991 on BS |

---

## 3. Journals

| Journal | Type | Sequence | Default Account | Purpose |
|---|---|---|---|---|
| Loan Disbursements | Bank | `LOAN-DISB` | 5030 | Outgoing disbursements |
| Loan Collections | Bank | `LOAN-COL` | 5031 | Incoming repayments |
| Loan Operations | Misc | `LOAN-OPS` | 4110 | Accruals, reclassifications, provisions |
| Loan Income Invoices | Sales | `LOAN-INV` | 7210 | Customer invoices (10-digit, no annual reset) |
| Penalty Journal | Misc | `LOAN-PEN` | 4961 | Daily Approach A penalty postings |

---

## 4. Disbursement — Journal Entries

### 4A. Gross Disbursement (full principal to client)

```
DR  4110  —  Вземания по кредити (Current 12-month portion)
DR  262   —  Дългосрочни заеми (Remaining LT portion)
    CR  5030  —  Bank Disbursements (total principal)
```

### 4B. Net Disbursement (fees/taxes deducted at source)

```
DR  4110 + 262  —  Loans Receivable (full principal)
    CR  5030     —  Bank (gross principal minus fees/taxes)
    CR  4950     —  Deferred Fee Revenue (if fee_recognition = 'amortised')
    CR  7220     —  Initial Fee Income  (if fee_recognition = 'immediate')
    CR  7250     —  Loan Tax Income     (stamp duty, registration taxes to client)
```

### 4C. Initial Fee / Tax Invoice (when `invoice_initial_fees = True`)

On disbursement date, auto-create Customer Invoice:
- **Journal:** Loan Income Invoices
- **Account:** 7220 (fees) and/or 7250 (taxes)
- **Partner:** client
- **Status:** immediately validated and matched to bank/payment

---

## 5. Interest Accrual — Effective Interest Method

Posted on each `installment_date` by daily cron:

```
DR  4960  —  Начислени лихви / Accrued Interest Receivable
    CR  7210  —  Приходи от лихви / Interest Income
```

### 5A. Installment Schedule Fields (`loan.payment.schedule`)

```python
installment_date              # Date: due date (basis for accrual + penalty start)
principal_amount              # Float: scheduled principal repayment
interest_amount               # Float: scheduled interest (EIM-calculated)
fee_amount                    # Float: fee component (if amortised)
outstanding_principal_open    # Float: opening principal balance this period
effective_interest_rate_period # Float: EIR for this period
accrual_move_id               # Many2one(account.move): posted accrual entry ID
accrual_status                # Selection: draft / posted / reversed
paid_principal                # Float: principal received against this installment
paid_interest                 # Float: interest received
paid_fee                      # Float: fee received
paid_penalty                  # Float: penalty received
status                        # Selection: unpaid/partial/paid/overdue/waived/cancelled
penalty_start_date            # Date: installment_date + penalty_grace_days (NEVER hardcoded)
days_overdue                  # Integer: computed — max(0, today - installment_date)
penalty_accrued_informational # Float: Approach A running GL balance (4961)
penalty_calculated_at_payment # Float: Approach B fresh calc on payment date
```

---

## 6. Penalty Interest — CASH BASIS ONLY (Logos НФИ)

> **Decision 2026-03-14:** Logos uses cash-basis penalty. Account `4961` is **NOT used**.
> No daily GL entries. Books stay clean until cash is received.
> `penalty_accrued_informational` is display-only — shown to staff and client, zero accounting impact.

### 6A. Configuration (NEVER hardcode)

```python
# res.config.settings fields:
penalty_rate_annual   = 0.1015   # 10.15% p.a. — ECB main rate + 8pp (Постановление №426/2014)
                                  # Update manually when ECB rate changes
penalty_divisor       = 365      # A/365F day-count convention
penalty_grace_days    = 0        # Days AFTER due date before penalty starts
                                  # 0 = penalty starts the day after due date
                                  # Configurable — NEVER hardcode
```

```python
# Computed on schedule line — DISPLAY ONLY, no GL:
penalty_start_date            = installment_date + timedelta(days=penalty_grace_days)
penalty_accrued_informational = unpaid_amount * (penalty_rate_annual / penalty_divisor) * overdue_days
```

### 6B. Formula

```python
daily_penalty_rate = penalty_rate_annual / penalty_divisor
overdue_days       = max(0, calculation_date - penalty_start_date)
unpaid_amount      = unpaid_principal_installment + unpaid_interest_installment
penalty_amount     = unpaid_amount * daily_penalty_rate * overdue_days
```

- `calculation_date` = `date.today()` for daily cron display, `payment_date` for wizard
- Penalty resets to zero after any payment — recalculates from new unpaid balance
- Each installment calculated independently — no cross-installment compounding
- No penalty on penalty (simple interest only)

### 6C. Daily Cron — Informational Only (NO journal entry)

**Cron runs daily.** For each overdue installment where `today > penalty_start_date`:

```python
inst.penalty_accrued_informational = (
    (inst.unpaid_principal + inst.unpaid_interest)
    * (penalty_rate_annual / penalty_divisor)
    * (today - inst.penalty_start_date).days
)
```

- **Zero DR/CR entries.** Books untouched.
- Purpose: client statement display, staff awareness, negotiation basis.
- `4961` account — **NOT used for Logos**.

### 6D. Payment Wizard — Three Penalty Options

When staff opens the payment wizard, `penalty_calculated_at_payment` is recalculated fresh
using `payment_date`. Staff chooses one of three options:

#### Option 1 — Full calculated penalty (default)
`penalty_to_pay = penalty_calculated_at_payment`

#### Option 2 — Waive penalty entirely
Staff checks **`exclude_penalty`** checkbox → `penalty_to_pay = 0.00`
- `penalty_accrued_informational` resets to 0 on the installment line
- Zero journal entries for penalty

#### Option 3 — Custom negotiated amount
Staff edits **`penalty_custom_amount`** field (editable Float in wizard)
→ `penalty_to_pay = penalty_custom_amount`
- Must be ≥ 0 and ≤ `penalty_calculated_at_payment`
- Allows partial waiver by management discretion

### 6E. Journal Entry — Posted ONLY When Cash Received

**Applies to Options 1 and 3 (any amount > 0):**

```
DR  5031  —  Bank Collections       (penalty_to_pay)
    CR  7230  —  Penalty Income      (penalty_to_pay)
```

**Single clean entry. No 4961. No reconciliation.**

After posting: `inst.paid_penalty += penalty_to_pay`, `inst.penalty_accrued_informational = 0`

### 6F. Fields on `customer.loan.lines` (installment line)

| Field | Type | Purpose |
|-------|------|---------|
| `penalty_accrued_informational` | Float | Daily calc — display only, no GL |
| `penalty_calculated_at_payment` | Float | Recalculated fresh when wizard opens |
| `penalty_custom_amount` | Float | Staff override — negotiated amount |
| `waive_penalty` | Boolean | Exclude penalty from this installment permanently |
| `paid_penalty` | Float | Running total of penalty actually received |
| `penalty_start_date` | Date | Computed: `emi_date + penalty_grace_days` |

---

## 7. Payment Processing — Global Sweep Allocation

> **Decision 2026-03-14:** Logos uses a **global 4-round sweep**, NOT a per-installment waterfall.
> Each round clears the same component across ALL installments (oldest first) before the next
> round begins. This matches ЗПК Art. 35 priority while giving maximum flexibility for
> partial payments that cover some installments fully and others partially.

### 7.0 Algorithm Overview

```
remaining = amount_paid
installments = all unpaid lines, sorted by emi_date ASC

Round 1 — ALL penalties (oldest installment first):
    for each inst: pay min(penalty_due, remaining) → DR 5031 / CR 7230

Round 2 — ALL fees (oldest installment first):
    for each inst: pay min(fee_due, remaining) → DR 5031 / CR 4113

Round 3 — ALL interest (oldest installment first):
    for each inst: pay min(interest_due, remaining) → DR 5031 / CR 4960

Round 4 — Principal FIFO (oldest installment first):
    for each inst: pay min(principal_due, remaining)
    → DR 5031 / CR 4112 (if overdue) or 4110 (if current)
    Partial payment on an installment is OK — stop when remaining = 0

Overpayment (remaining > 0 after Round 4):
    loan.credit_balance += remaining   (held for future installments)
```

### 7.1 Priority Order (ЗПК Art. 35)

| Round | Component | Journal Entry | Notes |
|---|---|---|---|
| 1 | Penalty | DR 5031 / CR 7230 | Cash basis only. Skip if `waive_penalty`. Custom amount allowed. |
| 2 | Fees | DR 5031 / CR 4113 | Clears fees receivable |
| 3 | Interest | DR 5031 / CR 4960 | Clears accrued interest receivable |
| 4 | Principal | DR 5031 / CR 4112 or 4110 | 4112 if `inst.status == 'overdue'`, else 4110 |

### 7.2 Code Structure (wizard/loan_payment_bg.py)

```python
def action_pay(self):
    remaining = self.amount_paid
    loan = self.loan_id
    installments = loan.loan_lines_ids.filtered(
        lambda l: l.remaining_amount > 0 and not l.display_type
    ).sorted('emi_date')
    move_lines = []

    # Round 1 — ALL penalties
    for inst in installments:
        if remaining <= 0:
            break
        if inst.waive_penalty:
            continue
        penalty_due = inst.penalty_accrued_informational - inst.paid_penalty
        if penalty_due > 0:
            pay = min(penalty_due, remaining)
            remaining -= pay
            inst.paid_penalty += pay
            inst.penalty_accrued_informational = max(0, inst.penalty_accrued_informational - pay)
            move_lines += [
                (0, 0, {'account_id': bank_acc.id,        'debit': pay,  'is_principal': False}),
                (0, 0, {'account_id': pen_income_acc.id,  'credit': pay}),
            ]

    # Round 2 — ALL fees
    for inst in installments:
        if remaining <= 0:
            break
        fee_due = inst.fee_amount - inst.paid_fee
        if fee_due > 0:
            pay = min(fee_due, remaining)
            remaining -= pay
            inst.paid_fee += pay
            move_lines += [
                (0, 0, {'account_id': bank_acc.id,        'debit': pay}),
                (0, 0, {'account_id': fees_recv_acc.id,   'credit': pay}),
            ]

    # Round 3 — ALL interest
    for inst in installments:
        if remaining <= 0:
            break
        interest_due = inst.interest_amount - inst.paid_interest
        if interest_due > 0:
            pay = min(interest_due, remaining)
            remaining -= pay
            inst.paid_interest += pay
            move_lines += [
                (0, 0, {'account_id': bank_acc.id,        'debit': pay}),
                (0, 0, {'account_id': accrued_int_acc.id, 'credit': pay}),  # clears 4960
            ]

    # Round 4 — Principal FIFO
    for inst in installments:
        if remaining <= 0:
            break
        principal_due = inst.installment_amount - inst.paid_principal
        if principal_due > 0:
            pay = min(principal_due, remaining)
            remaining -= pay
            inst.paid_principal += pay
            principal_acc = overdue_acc if inst.status == 'overdue' else st_loan_acc
            move_lines += [
                (0, 0, {'account_id': bank_acc.id,        'debit': pay}),
                (0, 0, {'account_id': principal_acc.id,   'credit': pay}),
            ]

    # Overpayment
    if remaining > 0:
        loan.credit_balance += remaining

    # Post single consolidated move
    self.env['account.move'].create({
        'journal_id': col_journal.id,
        'date': self.payment_date,
        'ref': f'{loan.name} — payment {self.payment_date}',
        'move_type': 'entry',
        'customer_loan_id': loan.id,
        'line_ids': move_lines,
    }).action_post()
```

### 7.3 Penalty Options in Wizard (3 choices per payment)

| Option | Field | `penalty_due` used |
|---|---|---|
| Full | (default) | `penalty_calculated_at_payment` — recalculated fresh on `payment_date` |
| Waived | `waive_penalty = True` | 0 — no JE, `penalty_accrued_informational` reset |
| Custom | `penalty_custom_amount` | staff-entered amount (≥ 0, ≤ calculated) |

### 7.4 On-Time Full Payment (example JE)

```
DR  5031  —  Bank Collections
    CR  4960  —  Accrued Interest Receivable   (Round 3: interest)
    CR  4113  —  Fees Receivable               (Round 2: fee, if any)
    CR  4110  —  Loans Receivable Current      (Round 4: principal)
```

### 7.5 Payment with Penalty (example JE)

```
DR  5031  —  Bank Collections
    CR  7230  —  Penalty Income                (Round 1: cash basis only)
    CR  4960  —  Accrued Interest Receivable   (Round 3)
    CR  4113  —  Fees Receivable               (Round 2, if any)
    CR  4110 / 4112  —  Loans Receivable       (Round 4: principal)
```

No 4961 entries. No reconciliation. Single `account.move` per payment.

### 7.6 Partial Payment

- Rounds exhaust `remaining` at any point — stop mid-round, mid-installment is OK
- Store per-installment: `paid_penalty`, `paid_interest`, `paid_fee`, `paid_principal`
- Remainder stays in 7230 (not accrued), 4960, 4113, 4110/4112
- Penalty recalculates from new unpaid balance next day (daily cron — informational)

### 7.7 Overpayment

- `remaining > 0` after Round 4 → `loan.credit_balance += remaining`
- NOT posted to 4950 — held in model field, applied to next installment automatically

---

## 8. Due Amount Calculation (Payment Wizard)

```python
total_due = (
    sum(installment.unpaid_principal for installment in overdue_installments)
  + sum(installment.unpaid_interest for installment in overdue_installments)
  + current_period_accrued_interest_to_payment_date   # daily calc
  + sum(penalty_per_installment to payment_date)       # Approach B
  + sum(installment.unpaid_fee for installment in all_due)
)

# Current period (not yet due) interest:
days_elapsed       = payment_date - last_installment_date
accrued_interest   = outstanding_principal * (annual_rate / 365) * days_elapsed
```

---

## 9. Payment Documents — Two Variants

### Config Field: `loan.contract.invoice_mode`

```python
invoice_mode = 'invoice_receipt'  # Variant A — invoice + receipt (default this client)
invoice_mode = 'receipt_only'     # Variant B — receipt only
```

### Variant A — Invoice + Receipt

1. Payment received → FIFO allocation calculated
2. Generate **Payment Receipt** document (see fields below)
3. For income components (7220/7230/7240/7250): auto-create Customer Invoice
   - Journal: Loan Income Invoices
   - Validate immediately → status: Paid
   - Link invoice numbers to Receipt
4. Interest clearing (4960 → 5031): journal entry only, NO invoice

### Variant B — Receipt Only

1. Same allocation logic
2. Generate Payment Receipt document
3. Income posted via JE to 7220/7230/7240/7250 directly — no Odoo invoice

### Payment Receipt Required Fields

```
receipt_number              # Auto: RCPT-XXXXXXXXXX (10-digit, no reset)
client_name                 # partner_id.name
client_identifier           # EGN or ЕИК (partner_id.vat)
loan_contract_number        # loan.name
payment_date                # Confirmed date
total_amount_received       # Bank line amount
penalty_paid                # Allocation result (Approach B confirmed)
interest_paid               # Allocation result
fee_paid                    # Allocation result
principal_paid              # Allocation result
remaining_principal_balance # 262 + 4110 + 4112 after posting
next_installment_date       # From schedule
next_installment_amount     # From schedule
days_overdue_cleared        # For info
invoice_numbers             # Variant A only
installments_covered        # List of dates settled
```

---

## 10. Reclassification — LT ↔ ST (Monthly)

**Cron: 1st of month, 07:00.** For each active loan:

```
# Move new 12-month window from LT to ST:
DR  4110  —  Loans Receivable Current
    CR  262   —  LT Loans Receivable

# Next day: reverse + re-post with updated amounts
```

**Overdue reclassification (daily cron):**

```
DR  4112  —  Overdue Loan Principal
    CR  4110  —  Loans Receivable Current
```

---

## 11. Special Scenarios

### 11A. Pre-Closure / Early Settlement

1. Calculate: `total_due = remaining_principal + daily_interest_to_date + penalty + pre_closure_fee`
2. `pre_closure_fee`: staff inputs % in wizard → `fee = outstanding_principal × pct`
3. Cancel all future installments (`status = 'cancelled'`)
4. Reverse all future posted accruals (`DR 7210, CR 4960`)
5. Prevent interest/penalty beyond closure date (ЗПК consumer right)
6. Final settlement JE:

```
DR  5031  —  Bank Collections
    CR  4110 + 4112  —  Current + Overdue Principal
    CR  262          —  LT Principal
    CR  4960         —  Accrued Interest to closure date
    CR  7230         —  Penalty (cash basis)
    CR  7240         —  Pre-closure fee income
```

7. Set `loan.status = 'closed'`. Generate receipt. Issue invoices per `invoice_mode`.

### 11B. Restructuring — Decrease Installment (Same Term)

1. Client pays all due to next installment date (overdue + accrued interest + penalties)
2. `remaining_principal = sum(unpaid principal after payment)`
3. Recalculate: same rate, same remaining term → new lower installment (annuity formula)
4. New schedule starts from `first_unpaid_original_installment_date`
5. Cancel old remaining installments. Create new schedule lines. Log event.

**Date rule:** If due date = 20th, client pays 1 July, catches up to 20 July:
- New plan start = 20 July
- Period covered by first new installment = 20 July → 20 August
- First new payment due = **20 August**

### 11C. Restructuring — Decrease Term (Same Installment)

Same catch-up as 11B. Then:

```python
monthly_rate = annual_rate / 12
N = -math.log(1 - (monthly_rate * remaining_principal) / fixed_installment) / math.log(1 + monthly_rate)
N = math.ceil(N)  # round up
```

Same date alignment rule as 11B.

---

## 12. Provision for Loan Losses

| DPD Bucket | Provision % |
|---|---|
| 0 – 30 | 1 – 2% |
| 31 – 60 | 10 – 25% |
| 61 – 90 | 50% |
| 91 – 180 | 75% |
| > 180 | 100% |

**Provision entry:**
```
DR  6290  —  Разходи за обезценка / Provision Expense
    CR  2991  —  Провизии / Allowance for Loan Losses
```

**Write-off entry:**
```
DR  2991  —  Allowance (use existing provision)
    CR  4110 / 4112 / 262  —  Loans Receivable (remove from BS)
```

---

## 13. Scheduled Actions (Crons)

| Cron | Time | Action |
|---|---|---|
| Post Interest Accruals | Daily 06:00 | `due_date == today` → post `DR 4960 / CR 7210`. Set `accrual_move_id`. |
| Post Penalty (Approach A) | Daily 06:30 | For overdue where `today > penalty_start_date`: post daily delta `DR 4961 / CR 7230`. |
| Mark Overdue Installments | Daily 07:00 | `due_date < today AND status != paid` → `status = overdue`, update `days_overdue`, reclassify to 4112. |
| LT/ST Reclassification | Monthly 1st, 07:00 | Per loan: new 12-month window. Post `262 → 4110`. Reverse next day. |
| Fee Amortisation | Monthly 1st, 07:30 | If `fee_recognition = 'amortised'`: `DR 4950 / CR 7220` per loan. |

---

## 14. Configuration Settings (`res.config.settings`)

```python
# Penalty
penalty_rate_annual          = fields.Float(default=0.1015)  # 10.15% p.a.
penalty_divisor              = fields.Integer(default=365)
penalty_grace_days           = fields.Integer(default=0)     # CONFIGURABLE — not hardcoded

# Document generation
default_invoice_mode         = fields.Selection([('invoice_receipt','Invoice + Receipt'),('receipt_only','Receipt Only')], default='invoice_receipt')
invoice_initial_fees         = fields.Boolean(default=True)  # Invoice for initial fees/taxes
fee_recognition_method       = fields.Selection([('immediate','Immediate'),('amortised','Amortised')], default='immediate')

# Journals
disbursement_journal_id      = fields.Many2one('account.journal')
collection_journal_id        = fields.Many2one('account.journal')
operations_journal_id        = fields.Many2one('account.journal')
invoice_journal_id           = fields.Many2one('account.journal')
penalty_journal_id           = fields.Many2one('account.journal')

# Accounts — Assets
lt_loan_account_id           = fields.Many2one('account.account')  # 262
st_loan_account_id           = fields.Many2one('account.account')  # 4110
overdue_loan_account_id      = fields.Many2one('account.account')  # 4112
fees_receivable_account_id   = fields.Many2one('account.account')  # 4113
accrued_interest_account_id  = fields.Many2one('account.account')  # 4960
penalty_receivable_account_id= fields.Many2one('account.account')  # 4961
allowance_account_id         = fields.Many2one('account.account')  # 2991

# Accounts — Income
interest_income_account_id   = fields.Many2one('account.account')  # 7210
fee_income_account_id        = fields.Many2one('account.account')  # 7220
penalty_income_account_id    = fields.Many2one('account.account')  # 7230
admin_fee_income_account_id  = fields.Many2one('account.account')  # 7240
tax_income_account_id        = fields.Many2one('account.account')  # 7250

# Accounts — Expense
provision_expense_account_id = fields.Many2one('account.account')  # 6290
```

---

## 15. Key Business Rules Summary

1. **Loan asset = full principal always.** Initial fees/taxes are separate income (7220/7250), never deducted from 4110/262.
2. **Interest = accrual basis** (4960/7210 at due date). No invoice. Receipt only.
3. **Penalty = cash basis** (informational daily cron, GL only at payment receipt — DR 5031/CR 7230). No 4961 GL entries.
4. **Penalty start = configurable** (`penalty_grace_days`). Default 0. Never hardcode.
5. **Penalty income = cash basis** at payment (7230). Daily `penalty_accrued_informational` is display-only, no JE.
6. **FIFO priority:** Penalty → Fee → Interest → Principal (ЗПК Art. 35). Global sweep across all installments.
7. **Invoice generation is optional** per `invoice_mode` and `invoice_initial_fees` config.
8. **Reclassification** LT ↔ ST runs monthly + daily overdue reclassification (4110→4112).
9. **Penalty resets** after any payment (full or partial). Recalculate from new unpaid balance.
10. **All JEs must carry:** `partner_id`, `loan_id`, `ref` (human-readable with loan name + date), `journal_id`.
11. **Installment dates are immutable** after loan activation (`status = in_progress`). See Rule 15 below.
12. **No automatic date adjustments** to existing loans. Holiday awareness applies only at schedule creation. See Rule 16 below.

---

## Rule 15: Installment Date Immutability

**Core rule:** Once `customer.loan.status == 'in_progress'`, `customer.loan.lines.emi_date` is **permanently readonly** for all automated processes.

**Why:** The installment date is the basis for:
- Interest accrual trigger (GROUP C cron fires on `emi_date`)
- Penalty start date (`emi_date + grace_days`)
- AnaCredit DPD reporting (days since `emi_date`)
- Journal entry dates on all posted moves
- Client contract obligations (signed document)

**The contract date = the system date. Always.**

**No automatic change may come from:**
- Holiday detection
- Weekend detection
- Any cron job (GROUP C, D, F, G)
- Any wizard (payment, pre-closure, restructure)
- Any script (import, setup)
- System upgrade or module update

**Technical enforcement:**

```python
def _write(self, vals):
    if 'emi_date' in vals:
        if not self.env.context.get('allow_annex_change'):
            if any(l.customer_loan_id.status == 'in_progress'
                   for l in self):
                raise UserError(
                    "Датата на вноска не може да бъде променяна "
                    "след активиране на кредита.")
        else:
            if not self.env.user.has_group(
                    'tk_loan_management.department_manager'):
                raise UserError(
                    "Само мениджър може да променя дата по анекс.")
    return super()._write(vals)
```

**Only allowed exception — Signed Annex (анекс):**
- Triggered with `context={'allow_annex_change': True}`
- Requires `group_loan_manager` permission
- Mandatory reason field
- Audit log entry created

**Restructure / pre-closure exception:**
These do NOT change existing `emi_date`. They **unlink future lines entirely** and create a new schedule.
Old lines are frozen at their original dates.

---

## Rule 16: Holiday-Aware Scheduling — New Loans Only

Holidays affect **only** initial schedule generation (pre-disbursement, `status = draft`).

**Correct flow:**
1. System calculates installment date mathematically
2. If date is public holiday or weekend → system **suggests** next business day
3. Loan officer **reviews and confirms** (human decision, not automatic)
4. Officer may override the suggestion if needed
5. Date is locked after disbursement — immutable from that point

**System may suggest, human must confirm. System never auto-applies.**

**Not affected by holiday logic:**
- Any existing in-progress loan (immutable)
- Penalty calculation (always calendar days from contract `emi_date`)
- Interest accrual cron (fires on exact `emi_date`, regardless of day of week)
- Any reclassification cron

**Holiday data source:** `resource.calendar.leaves` (populated by `setup_generic.py`).
Coverage: 2026–2035. Fixed holidays + Orthodox Easter + weekend compensation (КТ чл.154 ал.2).
Annual coverage check cron runs December 1st; notifies admin if coverage expires within 2 years.

---

*Version: 2.0 | VitoshaBG Accountancy | Bulgarian NAS НФИ Micro-Loan Lender*
