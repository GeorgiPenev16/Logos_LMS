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
- [ ] `models/anacredit_fields.py` — BNB (Bulgarian National Bank) reporting fields on `customer.loan`
- [ ] Fields: instrument type, purpose code, amortisation type, interest rate type, etc.
- [ ] `models/anacredit_report.py` — XML/CSV export logic
- [ ] Mapping from loan fields to AnaCredit schema
- [ ] Scheduled action for periodic reporting

## Priority Order
1. **Phase 0** — environment setup (in progress)
2. **Phase 1 + 2** — foundation and partner fixes (blocks everything else)
3. **Phase 3** — loan model fixes (blocks import scripts)
4. **Phase 5** — contract template (**blocks go-live** — no loan can be signed without correct contract)
5. **Phase 4** — ГПР (legal compliance, must be on every contract per ZPK)
6. **Phase 6 + 7** — scripts (needed for data migration before go-live)
7. **Phase 8** — AnaCredit (can be done post go-live)
