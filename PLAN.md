# VitoshaBG Loan Implementation Framework - Development Plan

## Phase 0: Environment Setup
- [x] Git installed and configured
- [x] GitHub repo Logos_LMS created
- [x] Odoo.sh Logos project created
- [x] TechKhedut invited to both
- [x] tk_loan_management v1.0.8 delivered
- [x] Code cloned to PC
- [x] CLAUDE.md, PLAN.md, INVESTIGATION.md, SESSION_LOG.md created
- [ ] Push all docs to GitHub
- [ ] Install tk_loan_management on Odoo.sh
- [ ] Create `tk_loan_management_bg` repo structure

## Phase 1: Module Foundation
- [ ] Create `tk_loan_management_bg/` module structure
- [ ] `__manifest__.py` with dependency on `tk_loan_management`
- [ ] `__init__.py` files (models, views, reports, security, data)
- [ ] `security/ir.model.access.csv` for new models
- [ ] Basic `i18n/bg.po` skeleton

## Phase 2: Partner/Contact Fixes ✅ COMPLETE (tested 2026-03-10)
- [x] `models/partner_bg.py` — company vs individual field separation
- [x] EIK validation on Odoo's built-in `company_registry` field (9 digits + checksum)
- [x] `manager_id` field (МОЛ — Материално Отговорно Лице) for companies
- [x] `bulstat` field for non-commercial entities (9 digits + checksum)
- [x] `is_guarantor` Boolean role (Поръчител)
- [x] Fix EGN/ID card to skip validation when `is_company=True`
- [x] `views/partner_bg_views.xml` — conditional visibility (`invisible="is_company"` / `invisible="not is_company"`)
- [x] Domain on codebtor/guarantor handled at loan level (see Phase 3)

## Phase 3: Loan Model Fixes ✅ COMPLETE (tested 2026-03-10, installment grid postponed)
- [x] `models/loan_bg.py` — inherit `customer.loan`
- [x] `represented_by` Many2one field (auto-fills from company МОЛ, hidden for individuals)
- [x] `customer.loan.codebtor.line` model — `partner_id` + `guarantee_percentage`
- [x] `customer.loan.guarantor.line` model — `partner_id` + `guarantee_percentage`
- [x] `codebtor_line_ids` One2many on loan (replaced M2M, unlimited rows)
- [x] `guarantor_line_ids` One2many on loan (replaced M2M, unlimited rows)
- [x] `views/loan_bg_views.xml` — represented_by field, editable list tabs with % column
- [x] `security/ir.model.access.csv` — access rules for both new line models
- [ ] ~~Editable installment grid~~ — **POSTPONED** (v1.0.8 prepayment wizard covers main use case)

> **v1.0.8 note:** Payment wizard (`loan.payment`) already exists for registering payments
> with allocation logic (interest → penalty → fee → principal) and prepayment with
> automatic installment recalculation (`action_recalculate_installment()`).
> Manual line editing is deprioritised — will revisit if a concrete client need arises.

## Phase 3b: Full Accounting Overhaul (spec: ACCOUNTING_SPEC.md, identified 2026-03-13)

> **Reference:** `ACCOUNTING_SPEC.md` is the authoritative source for all accounting logic.
> Read it before writing any accounting Python/XML. Bulgarian NAS, НФИ entity, EUR post-2026.
> Phase 3b supersedes the earlier 3b-1…3b-5 item list — fully regrouped below.

---

### GROUP A — Configuration & Chart of Accounts Foundation ✅ COMPLETE (2026-03-14, v1.0.12)
> Commits: `361bed0` (models + data), `37198d7` (settings view fix), `580c710` (hide base fields + auto-populate)

- [x] Extend `res.config.settings` with:
  - `penalty_rate_annual` Float (default 0.1015 — ECB+8pp, update manually)
  - `penalty_divisor` Integer (default 365)
  - `penalty_grace_days` Integer (default 0 — NEVER hardcode)
  - `default_invoice_mode` Selection (`invoice_receipt` / `receipt_only`)
  - `invoice_initial_fees` Boolean (default True)
  - `fee_recognition_method` Selection (`immediate` / `amortised`)
  - Journal fields: `lms_disbursement_journal_id`, `lms_collection_journal_id`, `lms_operations_journal_id`, `lms_invoice_journal_id`
  - Account fields (all Many2one `account.account`, prefixed `lms_`):
    - Assets: `lms_lt_loan_account_id` (262), `lms_st_loan_account_id` (4110), `lms_overdue_loan_account_id` (4112), `lms_fees_receivable_account_id` (4113), `lms_accrued_interest_account_id` (4960), `lms_allowance_account_id` (2991)
    - Income: `lms_interest_income_account_id` (7210), `lms_fee_income_account_id` (7220), `lms_penalty_income_account_id` (7230), `lms_early_repayment_income_account_id` (7240), `lms_other_income_account_id` (7250)
    - Expense: `lms_provision_expense_account_id` (6290)
- [x] Data file: 4 journals (LDISB, LCOL, LOPS, LINV) — `noupdate=1` — `data/account_journals_bg.xml`
- [x] Data file: Bulgarian NAS chart of accounts (18 accounts: 151, 152, 262, 2991, 4110, 4112, 4113, 4532, 4950, 4960, 5030, 5031, 7210–7250, 6290) — `noupdate=1` — `data/account_chart_bg.xml`
- [x] Settings view: "Loans (БГ)" app block in `res.config.settings` — `views/res_config_settings_bg_views.xml`
- [x] Base module per-loan fields hidden from UI; auto-populated via `default_get()` from `res.company.lms_*`

---

### GROUP B — Disbursement Overhaul ✅ COMPLETE (2026-03-14, v1.0.13)
> Commit: `2d91157` — `models/loan_disburse_bg.py`

- [x] `_compute_st_lt_split()`: sums `installment_amount` for lines with `emi_date ≤ disbursement_date + 12 months` → ST amount; LT = loan_amount − ST; clamped to [0, loan_amount]
- [x] Override `action_disburse_loan()`: calls `super()` (validations + mail + status), then replaces draft JE lines with `DR 4110 (ST) + DR 262 (LT) / CR 5031 (bank)`, posts move
- [x] Graceful fallback: if `lms_lt_loan_account_id` / `lms_st_loan_account_id` / `lms_disbursement_journal_id` not set in Settings → base behaviour runs unchanged
- [x] `_create_fee_invoice_bg()`: creates + validates `out_invoice` on LINV journal (7220) when `lms_fee_invoice_on_disburse=True` and `is_processing_fee` and `processing_fee_deduct_from='disbursement'`
- [ ] Deferred fee amortisation cron (monthly): `DR 4950 / CR 7220` per loan — deferred to post go-live

---

### GROUP C — Interest Accrual Cron ✅ COMPLETE (2026-03-14, v1.0.14)
> Commit: pending push — `models/loan_accrual_bg.py` + `data/cron_accrual_bg.xml`

- [x] `CustomerLoanLineAccrualBG` inherits `customer.loan.lines`: adds `accrual_move_id` Many2one, `accrual_status` Selection (draft/posted/reversed)
- [x] `CustomerLoanAccrualBG` inherits `customer.loan`: `_cron_post_interest_accrual()` — daily 06:00
  - Finds all `in_progress` loans; filters lines where `emi_date == today` AND `accrual_status != 'posted'` AND `interest_amount > 0`
  - Posts one `account.move` per line: DR 4960 (`interest_amount`) / CR 7210 (`interest_amount`)
  - Sets `accrual_move_id` + `accrual_status = 'posted'`; logs count
  - Skips gracefully with warning if accounts/journal not configured in Settings
  - Per-line try/except: one failed line doesn't block remaining loans
- [x] `data/cron_accrual_bg.xml`: `ir.cron` record, daily, priority=5, unlimited runs
- [ ] Advance payment partial reversal of 4960 accrual — deferred to GROUP E (payment wizard)

---

### GROUP D — Penalty System (Cash Basis — NO daily GL) ✅ COMPLETE (2026-03-14, v1.0.15)
> Commit: pending push — `models/loan_penalty_bg.py` + `data/cron_penalty_bg.xml`

- [x] Daily cron (informational, **zero journal entries**):
  - For each overdue installment where `today > penalty_start_date` and not `waive_penalty`:
  - `inst.penalty_accrued_informational = unpaid_base × (rate/divisor) × overdue_days`
  - No DR/CR. Display only. Purpose: client statement, wizard display, negotiation.
- [x] Add fields on `customer.loan.lines` (via `_inherit`):
  - `penalty_start_date` Date — computed: `emi_date + lms_penalty_grace_days` (stored)
  - `penalty_accrued_informational` Float — daily calc, display only, no GL
  - `penalty_calculated_at_payment` Float — recalculated fresh when payment wizard opens
  - `penalty_custom_amount` Float — staff-editable negotiated amount (Option 3)
  - `waive_penalty` Boolean — permanent waiver flag for this installment
  - `paid_penalty` Float — cumulative penalty actually received and posted (readonly)
- [x] Override base `_cron_installment_due_penalty()` → no-op (suppress base GL posting)
- [x] Override base `_cron_loan_overdue_penalty()` → no-op (suppress compound interest posting)
- [x] `waive_penalty = True`: skip daily calc, `penalty_accrued_informational = 0`, exclude from wizard

---

### GROUP E — Payment Wizard Overhaul ✅ COMPLETE (2026-03-14, v1.0.16)
> Commit: pending push — `wizard/loan_payment_bg.py` + `views/loan_payment_bg_views.xml`

- [x] Unlock `date` field in wizard (view xpath removes `readonly="1"`)
- [x] Fix FIFO order: **Penalty → Fee → Interest → Principal** (correct ЗПК Art. 35 order)
- [x] Penalty — **3 options** in wizard:
  - **Option 1 — Full** (`penalty_option='full'`): fresh calc to `payment_date` per overdue line; `penalty_calculated_display` shown readonly
  - **Option 2 — Waived** (`penalty_option='waived'`): all overdue lines set `waive_penalty=True`; `penalty_accrued_informational=0`; zero JE for penalty
  - **Option 3 — Custom** (`penalty_option='custom'` + `penalty_custom_amount_wizard`): custom amount consumed greedily from oldest overdue line; validated against per-line cap
  - JE: `DR 5031 / CR 7230` (`is_overdue_interest=True`). **No 4961. No reconciliation.**
- [x] Account mapping: 4960 (accrued interest), 4113 (fees receivable), 4110 (current principal), 4112 (overdue principal), 7230 (penalty income)
- [x] Overdue detection: `inst.emi_date < payment_date` → CR 4112; else CR 4110
- [x] Overpayment: `loan.credit_balance = remaining` (held for future installments)
- [x] One JE per installment (all components bundled) — compatible with base `_compute_amount()` flags
- [x] Graceful fallback to base if `lms_collection_journal_id` / core accounts not configured
- [x] Initial fee payment path unchanged (delegates to `super()`)
- [ ] Payment Receipt document — deferred (Phase 6 scripts / post go-live)
- [ ] Invoice generation per `invoice_mode` — deferred (post go-live)

---

### GROUP F — Reclassification & Overdue Status
> Depends on GROUP B.

- [ ] Monthly cron (1st of month, 07:00): per loan, compute new 12-month window → `DR 4110 / CR 262`; reverse next day
- [ ] Daily cron (07:00): installments where `emi_date < today AND status != paid` → `DR 4112 / CR 4110` + `status = overdue`
- [ ] Add `days_overdue` Integer computed on `customer.loan.lines`
- [ ] Mark Overdue Installments daily cron: sets `status = 'overdue'`, updates `days_overdue`

---

### GROUP G — Restructuring & Pre-closure
> Depends on GROUP E.

- [ ] **Decrease installment** (base exists, but fix accounts to use 4110/4112/262 split)
- [ ] **Decrease term** (new): formula from spec §11C:
  ```python
  N = -math.log(1 - (monthly_rate * remaining_principal) / fixed_installment) / math.log(1 + monthly_rate)
  N = math.ceil(N)
  ```
- [ ] **Pre-closure wizard**: staff inputs pre-closure fee %; compute total due; cancel future installments (`status='cancelled'`); reverse future accruals (`DR 7210 / CR 4960`); post final settlement JE (5031 / 4110+4112+262+4960+7230+7240); set `loan.status = 'closed'`; ЗПК right: no interest/penalty beyond closure date

---

### GROUP H — Provision for Loan Losses
> Can be done post go-live.

- [ ] DPD bucket table configurable in settings (0-30: 1-2%, 31-60: 10-25%, 61-90: 50%, 91-180: 75%, >180: 100%)
- [ ] Monthly provision cron: compute required provision per loan, post `DR 6290 / CR 2991`
- [ ] Write-off entry: `DR 2991 / CR 4110+4112+262`
- [ ] Provision report

## Phase 4: Financial Parameters ✅ COMPLETE (tested 2026-03-10)
- [x] `models/loan_gpr.py` — pyxirr-based IRR and XIRR (identical to Excel functions)
- [x] `eir_ifrs` computed field — EIR per IFRS 9, periodic rate (e.g. 2.012660 %/month)
- [x] `gpr` computed field — ГПР/APRC annual rate via XIRR on actual dates (e.g. 26.850392 %)
- [x] `total_cost_of_credit` computed monetary field
- [x] `total_amount_payable` computed monetary field
- [x] `_check_gpr_max` constraint — blocks confirmation if ГПР > 50 % (ZPK чл. 19, ал. 4)
- [x] `views/loan_gpr_views.xml` — Financial Parameters group on Loan Evaluation tab
- [x] APR label on `interest_rate` field (ANNLSD_AGRD_RT)
- [x] Warning banner when ГПР > 50 %
- [x] 6 decimal places on both EIR and ГПР (reporting standard)
- [ ] `models/loan_type_bg.py` — min/max loan amounts and terms per type (low priority, postponed)

> **Implementation notes:**
> - `pyxirr` added to `requirements.txt` — Odoo.sh installs it automatically
> - EIR = `excel_irr([-disbursed, +pmt1, …])` — periodic rate, NOT annualised
> - ГПР = `excel_xirr(dates, [-disbursed, +pmt1, …])` — annual, actual day fractions
> - Disbursement t₀ uses `disbursement_date` → `approval_date` → first line date
> - `account.move.line` `is_interest`/`is_principal`/`is_fee` flags available for AnaCredit (Phase 8)

## Phase 5: Document System ✅ COMPLETE (implemented 2026-03-10, build passing 2026-03-10)
- [x] `models/document_template.py` — `loan.document.template` with 7 document types and {placeholder} system
- [x] `models/loan_document.py` — `loan.generated.document` + `loan.document.generate.wizard`
- [x] Bulgarian number-to-words (`_number_to_bg_words`) for `{loan_amount_words}`
- [x] 26 placeholders: loan fields, borrower, guarantor/codebtor, company
- [x] PDF generation via QWeb (`loan_document_report.xml`)
- [x] DOCX generation via `python-docx` (optional, graceful fallback)
- [x] "Generate Document" button in existing Documents tab header (no new tab)
- [x] Generated docs list in Documents tab (separator + list, hidden when empty)
- [x] `views/document_template_views.xml` — form/list views + wizard form
- [x] Menu: Loans → Configuration → Document Templates
- [x] `data/document_templates_data.xml` — 3 default templates (noupdate=1):
  - Договор за кредит (full contract with signature lines)
  - Декларация ЗМИП/AML (AML declaration with checkboxes)
  - Запис на заповед (promissory note with amount in words)
- [x] `security/ir.model.access.csv` — access for new models
- [x] `python-docx` added to `requirements.txt`

> **Implementation notes:**
> - Templates are fully editable by admin via Loans → Configuration → Document Templates
> - `noupdate="1"` on data file — admin edits to default templates are preserved on upgrade
> - PDF generation uses `self.env.ref('tk_loan_management_bg.loan_document_report_action')`
> - DOCX is generated if `python-docx` is installed, silently skipped otherwise
> - The old hardcoded base module contract (Finance Hold) is not suppressed — use these templates instead
> - `{loan_amount_words}` uses Bulgarian number-to-words (e.g. "хиляда и двеста лева и 00 стотинки")

## Phase 6: Configuration Scripts
- [x] Logos company data entered manually in Odoo.sh staging via Settings → Company (2026-03-11)
      > **NOTE:** `setup_logos.py` must NOT overwrite company info — check before writing, skip if set
- [ ] `scripts/setup_generic.py` — journals, document types, holidays, system params
- [ ] `scripts/setup_logos.py` — loan types, interest rates, settings (company info: skip-if-set)
- [ ] `l10n_bg` dependency evaluated and added if needed
- [ ] `scripts/README.md` — usage instructions for all scripts
- [ ] All scripts use XML-RPC, `TEST_MODE=True` by default

## Phase 7: Import Scripts
- [ ] `scripts/import_contacts.py` — import borrowers/guarantors from Excel
  - [ ] Support both company (ЕИК) and individual (ЕГН) partners
  - [ ] Set roles (`is_loan_borrower`, `is_codebtor`, `is_guarantor`)
  - [ ] Import income/expense lines
  - [ ] Excel template generation (`--template`)
- [ ] `import_loans.py` (project root) — loan migration with backdated installments
  - [ ] Already created — validate and refine
  - [ ] Add guarantor/codebtor linking
  - [ ] Add ГПР calculation after import
- [ ] Excel templates for both scripts

> **Logos note:** `import_contacts.py` is critical because Logos has mostly company borrowers,
> not individuals. The script must handle `is_company=True` partners with ЕИК validation,
> МОЛ fields, and company-specific address formats — not just EGN-based individuals.
> Depends on Phase 2 (partner fields) being completed first.

## Phase 8: AnaCredit Integration
> **Reference:** `AnaCredit_CLAUDE.md` — full spec of the standalone generator script.
> **Strategy:** Odoo stores AnaCredit fields on `customer.loan` → export `CUCR_enhanced.csv`
> → feed into existing standalone `anacredit_generator_v3.0.py` → BNB submission.
> The generator script is already working (v3.1, EUR transition support). Odoo's job is to
> provide correctly populated data for it.

### GROUP AC-1 — AnaCredit Fields on `customer.loan`
- [ ] New model or `_inherit` extension: `models/anacredit_bg.py`
- [ ] Fields needed on `customer.loan`:
  | Odoo Field | CUCR Column | Source / Logic |
  |---|---|---|
  | `anacredit_rec` | `CUCR_REC` | Computed: 8=new disburse, 5=active, 7=restructured, 6=closed, 9=written-off |
  | `anacredit_bae` | `CUCR_BAE` | From `res.config.settings.anacredit_agent_id` (e.g. BGR00441) |
  | `anacredit_exp_nom` | `CUCR_EXP_NOM` | Computed: 70=performing (<30 DPD), 73=NPL (≥90 DPD) — per BNB table |
  | `anacredit_cred_spec` | `CRED_SPEC` | From `customer.loan.type` — new `anacredit_cred_spec` Char field |
  | `anacredit_grace_per` | `CRED_GRACE_PER` | Map from `grace_period` type: 90=fixed inst, 92=interest-only, 91=balloon |
  | `anacredit_jud_dues` | `CUCR_JUD_DUES` | New Monetary field — judgment dues |
  | `anacredit_tot_offbal` | `CUCR_TOT_OFFBAL` | New Monetary field — off-balance sheet |
  | Existing: `loan_amount` | `CUCR_SUMA` | Direct |
  | Existing: `interest_rate` | `CUCR_INTR` | Direct |
  | Existing: `approval_date` | `CRED_DAT1` | Direct |
  | Existing: `end_date` | `CRED_DAT2` / `DATF` | Direct |
  | From schedule: overdue principal | `CUCR_PRINC_OVER` | Computed from `loan_lines_ids` |
  | From schedule: overdue interest | `CUCR_OVER_INTER` | Computed from `loan_lines_ids` |
  | From schedule: days past due | `DAYS_PAST_DUE` | Computed from max overdue installment |
  | From partner: borrower type | `BORR_TYPE` | 1=EGN person, 2=EIK company, 3=BULSTAT |
  | From codebtor_line_ids | `CRED_CO_BORR` | First codebtor's EGN/EIK |
- [ ] `res.config.settings` additions: `anacredit_agent_id` Char (e.g. BGR00441), `anacredit_version` Char (default '0.9')
- [ ] `anacredit_cred_spec` Char field on `customer.loan.type` (maps to TYP_INSTRMNT via generator)

### GROUP AC-2 — CUCR_enhanced.csv Export from Odoo
- [ ] Wizard or scheduled action: `loan.anacredit.export.wizard`
- [ ] User selects report month → system queries all active loans for that period
- [ ] Generates `CUCR_enhanced.csv` with all required columns (semicolon-delimited, UTF-8)
- [ ] File downloadable from wizard or saved to configurable folder
- [ ] Validates mandatory fields before export (CRED_DAT1, CUCR_BORR, CUCR_CRED)
- [ ] Script version: XML-RPC export script `scripts/export_anacredit.py` as alternative

### GROUP AC-3 — Workflow & Documentation
- [ ] Document end-to-end workflow:
  `Odoo → Export Wizard → CUCR_enhanced.csv → anacredit_generator_v3.0.py → 10 BNB tables → BNB upload`
- [ ] `scripts/README.md` section: AnaCredit monthly procedure
- [ ] Validate CUCR_enhanced.csv output against known-good sample files
- [ ] Handle BGN legacy credits per-agent list (already in generator v3.1)

> **Note:** Groups AC-1 and AC-2 are post go-live. The standalone generator script is already
> operational and used in production. Odoo integration adds automation but is not a go-live blocker.

## Priority Order (updated 2026-03-13)

### Completed
- Phase 0 (env), Phase 1 (foundation), Phase 2 (partners), Phase 3 (loan model),
  Phase 4 (ГПР), Phase 5 (documents), Phase 6-address (ЕКАТТЕ settlements + partner lookup)

### Remaining — dependency order
| Step | What | Blocks |
|------|------|--------|
| ✅ 1 | **Phase 3b GROUP A** — config settings + chart of accounts + journals | Everything accounting |
| ✅ 2 | **Phase 3b GROUP B** — disbursement overhaul (4110+262 split, fee invoice) | GROUP F |
| ✅ 3 | **Phase 3b GROUP C** — interest accrual cron (4960/7210) | GROUP E |
| 4 | **Phase 3b GROUP D** — penalty overhaul (4961/7230, grace days, dual approach) | GROUP E |
| 5 | **Phase 6** — config scripts (`setup_generic.py`, `setup_logos.py`) | Phase 7 |
| 6 | **Phase 7** — import scripts (`import_contacts.py`, `import_loans.py`) | Go-live |
| 7 | **Phase 3b GROUP E** — payment wizard overhaul (FIFO fix, receipt, invoice) | Go-live |
| 8 | **Phase 3b GROUP F** — reclassification + overdue status crons | Post go-live |
| 9 | **Phase 3b GROUP G** — restructuring + pre-closure wizard | Post go-live |
| 10 | **Phase 3b GROUP H** — provision for loan losses | Post go-live |
| 11 | **Phase 8 AC-1** — AnaCredit fields on `customer.loan` + config | Post go-live |
| 12 | **Phase 8 AC-2** — `CUCR_enhanced.csv` export wizard/script | Post go-live |
| 13 | **Phase 8 AC-3** — workflow documentation + BNB submission validation | Post go-live |
