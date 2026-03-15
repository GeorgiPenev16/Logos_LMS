# Session Log: Complete Investigation & Actions

Date: 2025-02-24 (initial), 2026-03-05 (staging update)
Project: VitoshaBG Loan Management Framework
Paths: `C:\Odoo\LMS_21072025` (original v1.0.6), `C:\Odoo\Logos_LMS-staging` (current v1.0.8)

---

## Table of Contents

1. [Actions Taken](#1-actions-taken)
2. [Module Manifest & Dependencies](#2-module-manifest--dependencies)
3. [Complete File Inventory](#3-complete-file-inventory)
4. [All Models — Complete Catalog](#4-all-models--complete-catalog)
5. [customer.loan — Full Field Map](#5-customerloan--full-field-map)
6. [customer.loan.lines — Installment Schedule](#6-customerloanlines--installment-schedule)
7. [customer.loan.type — Loan Product Config](#7-customerloantype--loan-product-config)
8. [res.partner — Partner Extension](#8-respartner--partner-extension)
9. [account.move — Journal Entry Override](#9-accountmove--journal-entry-override)
10. [Settings Model (res.config.settings)](#10-settings-model-resconfigsettings)
11. [CRM Lead Integration](#11-crm-lead-integration)
12. [Dashboard Model](#12-dashboard-model)
13. [Supporting Models](#13-supporting-models)
14. [Security Groups & Wizards](#14-security-groups--wizards)
15. [Sequences](#15-sequences)
16. [Cron Jobs](#16-cron-jobs)
17. [Mail Templates](#17-mail-templates)
18. [Reports](#18-reports)
19. [Portal & Website Templates](#19-portal--website-templates)
20. [Frontend Assets](#20-frontend-assets)
21. [EMI Calculation — Exact Code](#21-emi-calculation--exact-code)
22. [Interest Rate Resolution Chain](#22-interest-rate-resolution-chain)
23. [Disbursement Journal Entry — Exact Structure](#23-disbursement-journal-entry--exact-structure)
24. [Installment Repayment Journal Entry — Exact Structure](#24-installment-repayment-journal-entry--exact-structure)
25. [Status Workflow — All Transitions](#25-status-workflow--all-transitions)
26. [EGN Validation — Full Algorithm](#26-egn-validation--full-algorithm)
27. [ID Card Validation](#27-id-card-validation)
28. [Bulgarian Number-to-Words](#28-bulgarian-number-to-words)
29. [Holiday-Aware Date Calculation](#29-holiday-aware-date-calculation)
30. [Codebtor Implementation — Gap Analysis](#30-codebtor-implementation--gap-analysis)
31. [Company vs Individual — Gap Analysis](#31-company-vs-individual--gap-analysis)
32. [Missing ГПР/XIRR — Gap Analysis](#32-missing-гпрxirr--gap-analysis)
33. [Contract Template — Hardcoded Issues](#33-contract-template--hardcoded-issues)
34. [Translation Coverage (bg.po)](#34-translation-coverage-bgpo)
35. [import_loans.py — Script Created](#35-import_loanspy--script-created)
36. [Documentation Files Created](#36-documentation-files-created)
37. [v1.0.8 Staging Differences](#37-v108-staging-differences)

---

## 1. Actions Taken

### Files Read & Analyzed
| File | Lines | What We Extracted |
|------|-------|-------------------|
| `__manifest__.py` | 109→112 | Dependencies, version, data files, assets (v1.0.6→v1.0.8) |
| `models/customer_loan.py` | 2512→2936 | All fields, 8 sub-models, all key methods (+424 lines in v1.0.8) |
| `models/customer_loan_type.py` | 152→~170 | Loan type config, term lines, doc lines (+overdue interest in v1.0.8) |
| `models/customer_loan_res_partner.py` | 267 | Partner fields, EGN validation, roles |
| `models/customer_loan_account_move.py` | ~40 | action_post() override |
| `models/customer_loan_res_config_settings.py` | ~60 | System settings fields |
| `models/customer_loan_dashboard.py` | ~200 | Dashboard data methods |
| `models/customer_loan_crm_lead.py` | ~300 | CRM lead integration, loan creation from lead |
| `models/customer_loan_product_template.py` | ~10 | Empty product inheritance |
| `models/public_holidays.py` | ~30 | Holiday model |
| `models/customer_collateral_type.py` | ~20 | Collateral type lookup |
| `models/customer_document_type.py` | ~20 | Document type lookup |
| `models/customer_installments_term_template.py` | ~80 | Term template with lines |
| `models/customer_repayments_terms_template.py` | ~30 | Repayment terms HTML template |
| `models/customer_terms_and_conditions_template.py` | ~30 | T&C HTML template |
| `views/res_partner.xml` | 108 | Partner form extension |
| `views/customer_loan_views.xml` | ~950 | Loan form/tree/kanban (partial) |
| `reports/loan_contract.xml` | ~1400 | Contract template (partial) |
| `data/ir_cron.xml` | 35 | 3 cron jobs |
| `data/sequence_data.xml` | 37 | 4 sequences |
| `security/groups.xml` | 19 | 2 security groups |
| `i18n/bg.po` | ~6000 | Bulgarian translations (searched) |

### Files Created
| File | Purpose |
|------|---------|
| `import_loans.py` (27KB) | Loan import script via XML-RPC |
| `CLAUDE.md` (6KB) | Project context for Claude Code sessions |
| `PLAN.md` (4KB) | Development plan with 8 phases |
| `INVESTIGATION.md` (15KB) | Investigation findings summary |
| `SESSION_LOG.md` (this file) | Comprehensive session log |

### Searches Performed
| Search | Result |
|--------|--------|
| APR / annual_percentage_rate / годишен процент | **Not found** |
| IRR / XIRR / internal rate of return | **Not found** |
| numpy / scipy / financial libraries | **Not found** |
| Total cost of credit / общ разход | **Not found** |
| rate_per_period / monthly rate | **Found** — simple `rate / periods / 100` |
| codebtor / co_debtor / съдлъжник | **Found** — on partner only, not on loan |
| поръчител / guarantor | **Found** — in contract template only (static text) |
| is_company / company_type / ЕИК / EIK | **Not found** in module code (only in contract static text) |

---

## 2. Module Manifest & Dependencies

```python
# __manifest__.py
'name': 'Customer Loan Management'
'version': '1.0.8'  # was 1.0.6 in original
'author': 'TechKhedut Inc.'
'license': 'OPL-1'
'application': True

'depends': [
    'base', 'crm', 'contacts', 'stock',
    'sale_management', 'account', 'portal',
    'website', 'accountant'
]
```

Heavy dependency chain — requires CRM, eCommerce (stock, sale), accounting, website, and portal modules.

**v1.0.8 additions to manifest data list:**
- `'data/revised_instalment_schedule_mail.xml'` — new mail template
- `'wizard/loan_payment_view.xml'` — new payment wizard view

---

## 3. Complete File Inventory

```
tk_loan_management/
├── __manifest__.py
├── __init__.py
│
├── models/
│   ├── __init__.py
│   ├── customer_loan.py                      (2512 lines - MAIN FILE)
│   ├── customer_loan_type.py                 (152 lines)
│   ├── customer_loan_res_partner.py          (267 lines)
│   ├── customer_loan_account_move.py         (~40 lines)
│   ├── customer_loan_res_config_settings.py  (~60 lines)
│   ├── customer_loan_dashboard.py            (~200 lines)
│   ├── customer_loan_crm_lead.py             (~300 lines)
│   ├── customer_loan_product_template.py     (~10 lines)
│   ├── customer_collateral_type.py           (~20 lines)
│   ├── customer_document_type.py             (~20 lines)
│   ├── customer_installments_term_template.py (~80 lines)
│   ├── customer_repayments_terms_template.py (~30 lines)
│   ├── customer_terms_and_conditions_template.py (~30 lines)
│   └── public_holidays.py                    (~30 lines)
│
├── wizard/
│   ├── __init__.py
│   ├── customer_loan_reject_reason_wizard.py + .xml
│   ├── customer_loan_cancel_reason_wizard.py + .xml
│   ├── customer_document_reject_reason_wizard.py + .xml
│   ├── customer_pre_closure_wizard.py + .xml
│   ├── customer_loan_settlement_wizard.py + .xml
│   ├── request_document_from_customer_wizard.py + .xml
│   ├── req_collateral_from_customer_wizard.py + .xml
│   └── customer_loan_portal_wizard_user.py
│
├── views/
│   ├── assets.xml
│   ├── customer_loan_views.xml               (main loan form/tree/kanban)
│   ├── customer_loan_type_views.xml
│   ├── customer_loan_account_move_views.xml
│   ├── customer_loan_crm_lead_inherit_view.xml
│   ├── customer_loan_res_config_settings_views.xml
│   ├── customer_installments_term_templates_views.xml
│   ├── customer_terms_and_conditions_template_views.xml
│   ├── customer_repayment_terms_template_views.xml
│   ├── customer_document_type_views.xml
│   ├── customer_collateral_type_views.xml
│   ├── res_partner.xml
│   ├── family_info_view.xml
│   ├── labour_relation_view.xml
│   ├── public_holidays_views.xml
│   ├── menu.xml
│   └── templates/
│       ├── customer_portal_template.xml
│       ├── lead_website_template.xml
│       ├── upload_document_template.xml
│       └── upload_collateral_template.xml
│
├── reports/
│   ├── loan_contract.xml                     (~1400 lines - Bulgarian contract)
│   ├── sanction_letter_report.xml
│   ├── closure_letter_report.xml
│   ├── noc_letter_report.xml
│   ├── settlement_letter_report.xml
│   └── signature_certificate_report.xml
│
├── data/
│   ├── sequence_data.xml                     (4 sequences)
│   ├── ir_cron.xml                           (3 cron jobs)
│   ├── sanction_letter_mail.xml
│   ├── customer_signed_loan_mail.xml
│   ├── loan_disbursement_confirmation_mail.xml
│   ├── installment_reminder_mail.xml
│   ├── installment_overdue_penalty_mail.xml
│   ├── document_request_mail.xml
│   ├── collateral_request_mail.xml
│   ├── loan_request_submitted_mail.xml
│   └── loan_request_approved_mail.xml
│
├── security/
│   ├── groups.xml                            (2 groups)
│   ├── ir.model.access.csv
│   └── ir_rules.xml
│
├── i18n/
│   └── bg.po                                (~95% translated)
│
└── static/
    └── src/
        ├── js/
        │   ├── script.js                     (frontend)
        │   ├── dashboard/
        │   │   └── customer_loan_dashboard.js
        │   └── lib/
        │       ├── apexcharts.js
        │       ├── xy.js
        │       ├── index.js
        │       ├── percent.js
        │       └── Animated.js
        ├── css/style.css
        ├── scss/style.scss
        └── xml/template.xml
```

---

## 4. All Models — Complete Catalog

### Primary Models (in customer_loan.py)
| # | Model | _name | Line | Records |
|---|-------|-------|------|---------|
| 1 | CustomerLoan | `customer.loan` | 1 | Main loan |
| 2 | CustomerLoanLines | `customer.loan.lines` | 2042 | Installments |
| 3 | CustomerLoanDocuments | `customer.loan.document.lines` | 2167 | Documents |
| 4 | CustomerCollateralLines | `customer.collateral.lines` | 2272 | Collateral |
| 5 | InstallmentPenaltyLines | `customer.loan.installment.penalty.lines` | 2315 | Penalties |
| 6 | CustomerLoanRequestedDocument | `customer.loan.request.document` | 2354 | Doc requests |
| 7 | CustomerLoanRequestedCollateral | `customer.loan.request.collateral` | 2380 | Col requests |
| 8 | CustomerLoanSanctionLatter | `customer.loan.sanction.latter` | 2413 | Sanction letters |

### Configuration Models
| # | Model | _name | File |
|---|-------|-------|------|
| 9 | CustomerLoanType | `customer.loan.type` | customer_loan_type.py |
| 10 | CustomerLoanTypeTermLines | `customer.loan.type.term.lines` | customer_loan_type.py:97 |
| 11 | LoanTypeDocumentLines | `loan.type.document.lines` | customer_loan_type.py:133 |
| 12 | CustomerTermTemplate | `customer.term.template` | customer_installments_term_template.py |
| 13 | CustomerTermTemplateLines | `customer.term.template.lines` | customer_installments_term_template.py |
| 14 | CustomerRepaymentTermsTemplate | `customer.repayment.terms.template` | customer_repayments_terms_template.py |
| 15 | CustomerTermsAndConditionsTemplate | `customer.terms.and.conditions.template` | customer_terms_and_conditions_template.py |

### Lookup/Type Models
| # | Model | _name | File |
|---|-------|-------|------|
| 16 | CustomerDocumentType | `customer.document.type` | customer_document_type.py |
| 17 | CustomerCollateralType | `customer.collateral.type` | customer_collateral_type.py |
| 18 | PublicHolidays | `public.holidays` | public_holidays.py |
| 19 | CustomerFamilyInfo | `family.info` | customer_loan_res_partner.py:251 |
| 20 | LabourRelation | `labour.relation` | customer_loan_res_partner.py:260 |

### Partner/Income Models
| # | Model | _name | File |
|---|-------|-------|------|
| 21 | CustomerIncomeLine | `customer.income.line` | customer_loan_res_partner.py:223 |
| 22 | CustomerExpenseLine | `customer.expense.line` | customer_loan_res_partner.py:235 |

### Inherited Models (no new _name)
| # | Model | _inherit | File |
|---|-------|----------|------|
| 23 | CustomerLoanResPartner | `res.partner` | customer_loan_res_partner.py |
| 24 | CustomerLoanAccountMove | `account.move` | customer_loan_account_move.py |
| 25 | CustomerLoanCrmLead | `crm.lead` | customer_loan_crm_lead.py |
| 26 | CustomerLoanProductTemplate | `product.template` | customer_loan_product_template.py |
| 27 | CustomerLoanProduct | `product.product` | customer_loan_product_template.py |
| 28 | CustomerLoanResConfigSettings | `res.config.settings` | customer_loan_res_config_settings.py |
| 29 | CustomerLoanDashboard | `customer.loan` | customer_loan_dashboard.py |

### Wizard Models (TransientModel)
| # | Model | Purpose |
|---|-------|---------|
| 30 | Reject Reason Wizard | Capture rejection reason |
| 31 | Cancel Reason Wizard | Capture cancellation reason |
| 32 | Document Reject Wizard | Reject uploaded document |
| 33 | Pre-Closure Wizard | Early loan closure |
| 34 | Settlement Wizard | Loan settlement |
| 35 | Request Document Wizard | Request docs from customer |
| 36 | Request Collateral Wizard | Request collateral from customer |
| 37 | Portal Wizard User | Portal user creation |
| 38 | Loan Payment **(v1.0.8)** | Payment registration with allocation (interest→penalty→fee→principal) |

**Total: 30 persistent models/inheritances + 9 wizards = 39 model classes** (v1.0.8)

---

## 5. customer.loan — Full Field Map

### Basic / Identity
```
name                    Char            Auto-generated CSL/XXXXX
lead_id                 M2O(crm.lead)   Source CRM lead
access_token            Char            Portal access token (secrets.token_urlsafe)
company_id              M2O(res.company) Required, default=env.company
currency_id             M2O(res.currency) Related to company currency
```

### Customer
```
customer_id             M2O(res.partner) Required
user_id                 M2O(res.users)
phone                   Char            Related(customer_id.phone), stored
email                   Char            Computed from user login or customer email
app_date                Date            Application date, default=today, required
```

### Requested Loan Details
```
approved_loan_type_id   M2O(customer.loan.type)
requested_loan_amount   Monetary
requested_start_date    Date            Default=today, required
requested_installment_type Selection    monthly/quarterly/yearly, default=monthly
requested_term          Integer
```

### Approved Loan Details
```
approval_date           Date
loan_amount             Monetary        Tracking=True
start_date              Date            Default=today, required, tracking=True
term                    Integer         Tracking=True
installment_type        Selection       monthly/quarterly/yearly, default=monthly
installment_amount      Monetary
interest_rate           Float
interest_amount         Monetary
```

### Computed Amounts
```
remaining_amount        Monetary        Computed
total_amount            Monetary        Computed
remaining_loan_principle_amount Monetary Computed
```

### Bank Details (Customer)
```
cst_bank_name           Char            Required
cst_bank_account_number Char            Required
cst_bank_branch_name    Char
cst_bank_branch_code    Char            Required
cst_bank_swift_bic_code Char            Required
```

### Fees
```
is_fee                  Boolean
fee_amount              Float           Per-installment fee percentage
is_initial_fee          Boolean
initial_fee_amount      Float
is_processing_fee       Boolean
processing_fee_deduct_from Selection    disbursement/customer, required
processing_fee_type     Selection       fixed/percentage
processing_fee_percentage Float         Default=1
processing_fee_amount   Monetary
processing_fee_tax_ids  M2M(account.tax)
```

### Grace Period
```
is_grace_period         Boolean
grace_period            Integer         In months
```

### Collateral
```
is_collateral           Boolean
collateral_ids          O2M(customer.collateral.lines)
is_collateral_added     Boolean         Default=True
compute_customer_collateral Boolean     Computed
req_collateral_ids      O2M(customer.loan.request.collateral)
```

### Penalty
```
is_penalty              Boolean
penalty_type            Selection       fixed/percentage, default=fixed
penalty_percentage      Float
penalty_amount          Monetary
outstanding_penalty     Monetary        Computed
penalty_tax_ids         M2O(account.tax)
penalty_lines_ids       O2M(customer.loan.installment.penalty.lines)
penalty_tooltip         Char
loan_od_count           Integer
```

### Installments
```
loan_lines_ids          O2M(customer.loan.lines)
installment_start_date  Date            Default=today, required
current_installment_amount Monetary
current_installment_due_date Date
end_date                Date            Computed, stored
```

### Disbursement
```
disbursement_payment_type Selection     cash/bank_transfer
disbursement_date       Date            Default=today
bill_id                 M2O(account.move) Vendor bill
bill_state              Selection       Related(bill_id.payment_state)
invoice_id              M2O(account.move) Processing fee invoice
invoice_state           Selection       Related(invoice_id.state)
```

### Accounting
```
receivable_account_id   M2O(account.account)  Domain: asset_receivable
bank_cash_account       M2O(account.account)  Domain: asset_cash
interest_income_account_id M2O(account.account) Domain: asset_receivable
journal_item_id         M2O(account.journal)  Disbursement journal
repayment_journal_item_id M2O(account.journal) Repayment journal
journal_entry_id        M2O(account.move)     Disbursement JE
```

### Documents
```
customer_loan_doc_ids   O2M(customer.loan.document.lines)
is_document_uploaded    Boolean         Default=True
compute_customer_doc    Boolean         Computed
req_document_ids        O2M(customer.loan.request.document)
```

### Sanction Letter
```
cst_conf_stage          Selection       draft/sent/signed/expired/rejected/cancelled (computed)
cst_response_stage      Selection       draft/reject_reopen/reopen_expired (computed)
sent_date_time          Datetime
accept_date_time        Datetime
expiry_date             Date            Computed, stored
is_expired              Boolean
cst_sign                Image
sign_by                 Char
signature_hash          Char
event_hash              Char
cst_loan_reject_reason  Text
sanction_latter_ids     O2M(customer.loan.sanction.latter)
send_revised_sanction_letter Boolean
```

### Settlement
```
settlement_date         Date
settlement_invoice_id   M2O(account.move)
settlement_invoice_state Selection      Related
settlement_amount       Monetary
forgiven_debt           Monetary
show_settlement         Boolean         Computed
settlement_journal_entry_id M2O(account.move)
```

### Terms
```
terms_and_conditions_template_id M2O(customer.terms.and.conditions.template)
terms_and_conditions    Html
repayment_terms_template_id M2O(customer.repayment.terms.template)
repayment_terms         Html
```

### Status & Workflow
```
status                  Selection       See section 25
responsible_id          M2O(res.users)  Default=env.user, required, tracking=True
reject_reason           Text            Tracking=True
cancel_reason           Text            Tracking=True
loan_purpose            Text
```

### Closure
```
loan_closure_date       Date
total_penalty           Monetary        Computed
is_pre_closure          Boolean
is_settlement           Boolean
```

### Portal
```
customer_loan_portal_url Char           Computed
customer_requested_document_portal_url Char Computed
```

---

## 6. customer.loan.lines — Installment Schedule

```
customer_loan_id        M2O(customer.loan)
display_type            Selection       line_section (for section headers)
name                    Text
emi_date                Date            "Date" — installment due date
installments_no         Char            "Installment No."
installment_amount      Monetary        Principal portion
interest_amount         Monetary        Interest portion
total_installment_amount Monetary       Principal + Interest
fee_amount              Monetary        Per-installment fee
total_paid_amount       Monetary
remaining_amount        Monetary
principal_balance       Monetary        Running balance

invoice_id              M2O(account.move)     Payment invoice
invoice_state           Selection             Related(invoice_id.state)
invoice_paid_date       Date                  Computed from payment records
journal_entry_id        M2O(account.move)     Repayment journal entry

installment_od_count    Integer               Overdue counter
penalty_invoice_id      M2O(account.move)
penalty_journal_entry_id M2O(account.move)
previous_installment_id M2O(customer.loan.lines)
is_count_set            Boolean
```

### Key Method: `action_create_journal_entry()` (line 2120)
- Validates: repayment journal, bank account, receivable account, interest income account
- Creates journal entry with 3 lines (bank debit, receivable credit, interest credit)
- Links via `journal_entry_id`

---

## 7. customer.loan.type — Loan Product Config

```
product_id              M2O(product.product)  Delegation inheritance (_inherits)
type                    Selection             Default='service' (from product)
company_id              M2O(res.company)
currency_id             M2O(res.currency)     Related to company

is_interest             Boolean               "Apply Interest" toggle
interest_rate           Float                 Base rate

term_template_id        M2O(customer.term.template) Template for term lines
term_lines_ids          O2M(customer.loan.type.term.lines) Rate overrides by term

is_fee                  Boolean               Per-installment fee toggle
fee_amount              Float                 Fee percentage (validated > 0 if enabled)
is_initial_fee          Boolean               Upfront fee toggle
initial_fee_amount      Float                 Upfront fee amount

loan_doc_ids            O2M(loan.type.document.lines) Required document types

terms_and_conditions_template_id M2O  → terms_and_conditions Html
repayment_terms_template_id M2O       → repayment_terms Html
```

### Term Lines (`customer.loan.type.term.lines`)
```
loan_type_id            M2O(customer.loan.type)
duration                Integer         "Upto (Installments)"
interest_rate           Float           Must be >= 0
installment_type        Selection       monthly/quarterly/yearly
```
Constraint: no duplicate `(duration, installment_type)` pairs per loan type.

---

## 8. res.partner — Partner Extension

### All Fields Added
```
personal_number         Char            EGN (10-digit Bulgarian personal number)
id_card                 Char            ID card number
validity_type           Selection       10_years / indefinite
date_of_issuing         Date            ID card issue date
date_of_validity        Date            Computed: issue + 10 years
issued_by               Char            Issuing authority

is_loan_borrower        Boolean         Role: Loan Borrower
is_person_of_contact    Boolean         Role: Person of Contact
is_codebtor             Boolean         Role: Codebtor

codebtor_ids            M2M(res.partner) Partner's codebtors

family_info_id          M2O(family.info)
no_of_children          Integer
date_of_salary_to       Selection       10/20/30

labour_relation_id      M2O(labour.relation)
employer                Char
ep_street               Char
ep_street2              Char
ep_city                 Char
ep_zip                  Char
ep_state_id             M2O(res.country.state)
ep_country_id           M2O(res.country)

income_line_ids         O2M(customer.income.line)
expense_line_ids        O2M(customer.expense.line)
total_income            Monetary        Computed
total_expense           Monetary        Computed

bank_account            Char
payment_method          Selection       cash/bank_transfer
notes                   Html
```

### View Layout (res_partner.xml)
All fields shown under "Other Info" tab. NO visibility conditions on `is_company`.
- `personal_number` — required="1"
- `id_card` — required="1"
- `date_of_issuing` — required="1"

---

## 9. account.move — Journal Entry Override

### Fields Added
```
customer_loan_id        M2O(customer.loan)
customer_installment_id M2O(account.move)
entry_post_date         Date
is_disbursement         Boolean
```

### action_post() Override
```python
def action_post(self):
    res = super().action_post()
    for rec in self:
        if rec.customer_loan_id and rec.move_type == 'entry' and rec.is_disbursement:
            rec.entry_post_date = fields.Date.today()
            # Sends disbursement confirmation email
            mail_template.send_mail(rec.customer_loan_id.id, force_send=True)
    return res
```

---

## 10. Settings Model (res.config.settings)

```
sanction_letter_expire_days  Integer    Days until sanction letter expires (must be > 0)
processing_fee_id            M2O(product.product) Processing fee product
processing_fee_status        Selection  draft/posted
installment_id               M2O(product.product) Installment product
installment_reminder_days    Integer    Days before due date to send reminder (must be > 0)
penalty_id                   M2O(product.product) Penalty product
pre_closure_charge_id        M2O(product.product) Pre-closure charge product
pre_closure_interest_id      M2O(product.product) Pre-closure interest product
pre_closure_installment_id   M2O(product.product) Pre-closure installment product
settlement_id                M2O(product.product) Settlement product
sales_person_id              M2O(res.users) Default salesperson
```

All stored via `ir.config_parameter` (Odoo system parameters).

---

## 11. CRM Lead Integration

### Fields Added to crm.lead
```
access_token, app_date, requested_start_date
approved_loan_type_id, requested_loan_amount, requested_term, requested_installment_type
cst_bank_name, cst_bank_account_number, cst_bank_branch_name, cst_bank_branch_code
cst_bank_swift_bic_code
customer_loan_id        M2O(customer.loan)  Created loan link
crm_customer_doc_ids    O2M(crm.customer.loan.document.lines)
terms_and_conditions, repayment_terms (Html)
loan_req_status, disbursement_payment_type, payment_method
Employer address fields (ep_street, ep_city, ep_country_id, etc.)
```

### Key Method: action_create_customer_loan()
Creates a `customer.loan` record from lead data, copies all fields, sets lead status.

### Sub-model: crm.customer.loan.document.lines
```
crm_lead_id             M2O(crm.lead)
document_type_id        M2O(customer.document.type)
document                Binary
file_name               Char
```

---

## 12. Dashboard Model

Extends `customer.loan` with dashboard methods (no new fields):

- `get_customer_loan_dashboard()` — returns JSON with:
  - Loan counts by status (draft, in_progress, closure, etc.)
  - Disbursement amounts by month (chart data)
  - Top 10 loan types
  - Total amount given vs recovered
  - Total charges collected (penalties + processing fees)
  - Overdue installments list
  - Unpaid penalties list
- `_get_disbursed_loan_by_month()`
- `_get_most_selling_loan_type()`
- `_get_total_loan_amount_given_and_recovered()`
- `_get_received_charges_amount()`
- `_get_overdue_installments_loans()`
- `_get_unpaid_penalties_loans()`

Frontend: uses ApexCharts library (bundled in static/src/js/lib/).

---

## 13. Supporting Models

### public.holidays
```
name        Char
start_date  Date
end_date    Date
status      Selection   draft/confirmed
```
Used by installment date calculation to skip holidays.

### customer.document.type
```
name        Char        Required, unique
```

### customer.collateral.type
```
name        Char        Required, unique
```

### customer.term.template + lines
Template for term-based interest rates. Can be applied to loan types via onchange.
```
Template: name, template_line_ids
Lines: duration, interest_rate, installment_type
```

### customer.terms.and.conditions.template
```
name                    Char        Required, unique
terms_and_conditions    Html
```

### customer.repayment.terms.template
```
name                    Char        Required, unique
repayment_terms         Html
```

### family.info
```
name        Char        Title (e.g. "Married", "Single")
```

### labour.relation
```
name        Char        Title (e.g. "Permanent", "Contract")
```

### customer.income.line
```
type        Char        Income type description
amount      Monetary
customer_id M2O(res.partner)
```

### customer.expense.line
```
type         Char
company_name Char        Creditor name
amount       Monetary
monthly_payment Monetary
customer_id  M2O(res.partner)
```

---

## 14. Security Groups & Wizards

### Security Groups
```xml
<!-- Category -->
module_category_tk_loan_management  "Customer Loan Management"

<!-- Groups -->
department_manager                  "Department Manager"
    → Default members: root, admin
    → Used for: document approval, status changes

create_loan_installment_invoice_access  "Create Loan Installment Entry Access"
    → No default members
    → Used for: manual installment journal entry creation
```

### Wizards (TransientModel)
| Wizard | Purpose | Key Fields |
|--------|---------|------------|
| Reject Reason | Capture loan rejection reason | `reject_reason` Text |
| Cancel Reason | Capture loan cancellation reason | `cancel_reason` Text |
| Document Reject | Reject uploaded document with reason | `reason` Char |
| Pre-Closure | Calculate early closure amounts | Charges, interest, amounts |
| Settlement | Calculate settlement with debt forgiveness | `settlement_amount`, `forgiven_debt` |
| Request Document | Send document request to customer portal | Document type selection |
| Request Collateral | Send collateral request to customer portal | Collateral type selection |
| Portal User | Create portal user for customer | Standard portal wizard |

---

## 15. Sequences

| ID | Code | Prefix | Padding | Purpose |
|----|------|--------|---------|---------|
| `customer_loan_sequence` | `customer.loan.sequence` | CSL/ | 5 | Loan number (CSL/00001) |
| `customer_loan_req_doc_sequence` | `customer.loan.req.doc.sequence` | LRD/ | 6 | Doc request (LRD/000001) |
| `customer_loan_req_col_doc_sequence` | `customer.loan.req.col.doc.sequence` | LRC/ | 6 | Collateral request (LRC/000001) |
| `customer_loan_sanction_letter_sequence` | `customer.loan.sanction.letter.sequence` | CLS/ | 6 | Sanction letter (CLS/000001) |

All sequences: `company_id = False` (shared across companies).

---

## 16. Cron Jobs

### 1. Payment Due Reminder & Entry Creation
```
Method: _cron_send_installment_reminder_create_invoice()
Interval: Daily
Purpose: Sends email reminder N days before installment due date
         (N = installment_reminder_days from settings)
```

### 2. Installment Due Penalty
```
Method: _cron_installment_due_penalty()
Interval: Daily
Purpose: Creates penalty entries for overdue installments
         Applies penalty based on loan's penalty_type (fixed/percentage)
```

### 3. Loan Overdue Penalty
```
Method: _cron_loan_overdue_penalty()
Interval: Daily
Purpose: Applies compound penalty on loans with multiple overdue installments
         Escalating penalties based on od_count
```

All three run daily and are active by default.

---

## 17. Mail Templates

| Template | Event |
|----------|-------|
| `sanction_letter_mail` | Sanction letter sent to customer |
| `customer_signed_loan_mail` | Customer signed the sanction letter |
| `loan_disbursement_confirmation_mail` | Loan disbursed (sent on JE post) |
| `installment_reminder_mail` | Upcoming installment reminder |
| `installment_overdue_penalty_mail` | Penalty applied on overdue installment |
| `document_request_mail` | Document requested from customer |
| `collateral_request_mail` | Collateral requested from customer |
| `loan_request_submitted_mail` | Loan request submitted (from website) |
| `loan_request_approved_mail` | Loan request approved |
| `revised_instalment_schedule_mail` **(v1.0.8)** | Revised schedule after prepayment |

---

## 18. Reports

| Report | Content |
|--------|---------|
| `loan_contract.xml` | Full loan contract (~1400 lines, Bulgarian legal text, **hardcoded company**) |
| `sanction_letter_report.xml` | Sanction/approval letter |
| `closure_letter_report.xml` | Loan closure confirmation |
| `noc_letter_report.xml` | No Objection Certificate |
| `settlement_letter_report.xml` | Settlement confirmation |
| `signature_certificate_report.xml` | Digital signature certificate |

---

## 19. Portal & Website Templates

| Template | Purpose |
|----------|---------|
| `customer_portal_template.xml` | Customer portal — view loan, installments, documents |
| `lead_website_template.xml` | Website loan application form |
| `upload_document_template.xml` | Portal document upload page |
| `upload_collateral_template.xml` | Portal collateral upload page |

---

## 20. Frontend Assets

### Backend (web.assets_backend)
- `template.xml` — OWL component template for dashboard
- `style.scss` — Dashboard styles
- `customer_loan_dashboard.js` — OWL dashboard component
- `apexcharts.js` — Chart library (bundled)
- `xy.js`, `index.js`, `percent.js`, `Animated.js` — amCharts5 modules (bundled)

### Frontend (web.assets_frontend)
- `script.js` — Portal JS (signature pad, document upload)
- `style.css` — Portal styles

---

## 21. EMI Calculation — Exact Code

Location: `customer_loan.py:1343-1361`

```python
def _calculate_emi(self, loan_amount, interest_rate, term, installment_type):
    periods_per_year = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
    periods = periods_per_year.get(installment_type, 12)
    rate_per_period = interest_rate / periods / 100

    if self.is_grace_period:
        term -= self.grace_period

    if rate_per_period != 0:
        emi = round(
            (loan_amount * rate_per_period * (1 + rate_per_period) ** term) / (
                    (1 + rate_per_period) ** term - 1), 2
        )
    else:
        emi = loan_amount / term

    total_amount = round(emi * term, 2)
    return emi, total_amount
```

Standard PMT/annuity formula. No APR, no XIRR, no total cost of credit.

---

## 22. Interest Rate Resolution Chain

Location: `customer_loan.py:1321-1341` (`_get_interest_rate()`)

```
1. If loan.interest_rate > 0 → return loan.interest_rate (manual override)
2. Else if loan_type has term_lines_ids:
   → Find line where duration >= loan.term AND installment_type matches
   → Return that line's interest_rate
3. Else if loan_type.is_interest == True:
   → Return loan_type.interest_rate (base rate)
4. Otherwise → return 0
```

---

## 23. Disbursement Journal Entry — Exact Structure

Location: `customer_loan.py:1683-1758` (`action_disburse_loan()`)

**Validations before creation:**
1. Processing fee > 0 if enabled
2. Processing fee invoice paid if deducted from customer
3. `bank_cash_account` must be set
4. `receivable_account_id` must be set

**Basic journal entry (no processing fee from disbursement):**
```
Debit:  receivable_account_id    loan_amount    partner=customer_id
Credit: bank_cash_account        loan_amount    partner=company.partner_id
```

**With processing fee deducted from disbursement (additional lines):**
```
Debit:  bank_cash_account           processing_fee_amount  partner=company + tax
Credit: interest_income_account_id   processing_fee_amount  partner=customer + tax
```

**Journal entry record:**
```python
{
    'journal_id': self.journal_item_id.id,
    'ref': self.name,                    # e.g. "CSL/00001"
    'move_type': 'entry',
    'customer_loan_id': self.id,
    'is_disbursement': True,             # triggers email on post
    'line_ids': journal_lines
}
```

Also sends disbursement email directly (before posting).

---

## 24. Installment Repayment Journal Entry — Exact Structure

Location: `customer_loan.py:2120-2164` (`action_create_journal_entry()` on `customer.loan.lines`)

**Validations:**
1. `repayment_journal_item_id` must be set
2. `bank_cash_account` must be set
3. `receivable_account_id` must be set
4. `interest_income_account_id` must be set

**Journal entry (3 lines):**
```
Debit:  bank_cash_account           total_installment_amount  partner=company
Credit: receivable_account_id       installment_amount        partner=customer
Credit: interest_income_account_id  (total - installment)     partner=customer
```
Where `total - installment_amount` = interest portion.

**Journal entry record:**
```python
{
    'journal_id': loan.repayment_journal_item_id.id,
    'ref': rec.installments_no,          # e.g. "1", "2", "3"
    'move_type': 'entry',
    'customer_loan_id': loan.id,
    'line_ids': journal_lines
}
```

No `is_disbursement` flag → posting does NOT send email.

---

## 25. Status Workflow — All Transitions

```
Value             Label
─────────────────────────────────────────
draft             Draft                 Initial state
confirm           Confirm               After basic validation
dept_approval     Department Approval   After dept review
confirmation      Confirmation          After documents verified
disbursement      Disbursement          Ready to disburse
in_progress       In Progress           Loan active
closure           Closure               Normal completion
pre_closure       Pre Closure           Early payoff
settlement        Settlement            Negotiated settlement
rejected          Rejected              Application denied
cancel            Cancelled             Loan cancelled
```

Status uses `group_expand="_group_expand_status"` for kanban columns.

---

## 26. EGN Validation — Full Algorithm

Location: `customer_loan_res_partner.py:136-204`

```python
@staticmethod
def is_valid_egn(egn: str):
    # 1. Must be exactly 10 digits
    if not re.match(r'^\d{10}$', egn): return False

    # 2. Extract date parts
    year_part = int(egn[0:2])
    month_part = int(egn[2:4])
    day_part = int(egn[4:6])

    # 3. Century detection
    if 41 <= month_part <= 52:      # 21st century (2000-2099)
        year = 2000 + year_part
        month = month_part - 40
    elif 21 <= month_part <= 32:    # 19th century (1800-1899)
        year = 1800 + year_part
        month = month_part - 20
    elif 1 <= month_part <= 12:     # 20th century (1900-1999)
        year = 1900 + year_part
        month = month_part

    # 4. Validate calendar date
    date(year, month, day_part)     # raises ValueError if invalid

    # 5. Checksum
    weights = [2, 4, 8, 5, 10, 9, 7, 3, 6]
    checksum = sum(int(egn[i]) * weights[i] for i in range(9)) % 11
    if checksum == 10: checksum = 0
    return checksum == int(egn[9])
```

Returns `(True, None)` or `(False, error_message)`.

---

## 27. ID Card Validation

Location: `customer_loan_res_partner.py:206-220`

```python
@staticmethod
def is_valid_id_card(id_card: str) -> bool:
    pattern_digits = r'^\d{9}$'           # 9-digit number
    pattern_alpha_num = r'^[A-Z]{2}\d{7}$'  # 2 uppercase letters + 7 digits
    return bool(re.match(pattern_digits, id_card) or
                re.match(pattern_alpha_num, id_card))
```

---

## 28. Bulgarian Number-to-Words

Location: `customer_loan.py:23-100+`

Implements full Bulgarian number-to-words conversion with:
- Masculine/feminine/neuter forms (`_UNITS_MASCULINE`, `_UNITS_FEMININE`, `_UNITS_NEUTER`)
- Numbers 0-999,999,999+
- Used in contract reports for writing amounts in words

---

## 29. Holiday-Aware Date Calculation

### Public Holiday Check
```python
def _get_public_holiday_dates(self):
    # Returns set of dates with status='confirmed'
    holidays = self.env['public.holidays'].search([('status', '=', 'confirmed')])
    # Expands date ranges into individual dates
```

### Installment Date Adjustment
```python
def _get_valid_installment_date(self, target_date):
    # If target_date is Sunday or holiday, moves BACKWARD
    # Keeps moving back until a valid business day is found
```

### Month Advancement
```python
def _get_new_valid_target_date(self, current_date, step_months, installment_day):
    # Advances by step_months
    # Handles month-end edge cases (e.g., Jan 31 → Feb 28)
    # Then applies _get_valid_installment_date()
```

---

## 30. Codebtor Implementation — Gap Analysis

### What EXISTS
On `res.partner`:
- `is_codebtor` Boolean flag (checkbox in "Roles" section)
- `codebtor_ids` Many2many(res.partner) with relation table `loan_codebtor_rel_res_partner`

### What's WRONG
1. **Not on the loan** — `customer.loan` has zero codebtor fields
2. **No domain filter** — any partner can be tagged as codebtor of anyone
3. **No guarantor role** — only "Codebtor", but contract uses "Поръчител" (guarantor)
4. **Partner-level only** — codebtors belong to a person, not a specific loan
5. **Contract placeholders static** — guarantor section uses `___________`, not field values

### Translation in bg.po
```
"Codebtor" → "Съдлъжник" (but contract says "Поръчител" = guarantor)
"Codebtor Details" → "Подробности за съдлъжника"
```

---

## 31. Company vs Individual — Gap Analysis

### What EXISTS
All partner fields are shown regardless of `is_company`:
- `personal_number` (EGN) — **required="1"**, no `invisible` condition
- `id_card` — **required="1"**, no `invisible` condition
- `date_of_issuing` — **required="1"**, no visibility condition
- Family, employer, salary fields — always visible

### What's MISSING
| Field | Status |
|-------|--------|
| `invisible="is_company"` on EGN/ID card | **Not implemented** |
| ЕИК (company ID, 9 or 13 digits) | **No field exists** |
| БУЛСТАТ | **No field exists** |
| МОЛ (company representative) | **No field exists** |
| Company registry fields | **Not used** |
| Different validation for companies | **Not implemented** |

### Constraint Issue
`_check_personal_number()` always validates as EGN. A company partner cannot save without a valid 10-digit EGN — which companies don't have.

---

## 32. Missing ГПР/XIRR — Gap Analysis

### What EXISTS
Only a simple PMT formula:
```python
rate_per_period = interest_rate / periods / 100
emi = (P * r * (1+r)^n) / ((1+r)^n - 1)
```

### What's MISSING
| Calculation | Status |
|-------------|--------|
| APR / ГПР (Годишен Процент на Разходите) | **Not implemented** |
| IRR (Internal Rate of Return) | **Not implemented** |
| XIRR (for irregular cash flows) | **Not implemented** |
| Total cost of credit | **Not computed** |
| numpy / scipy / numpy_financial | **Not imported** |
| Max ГПР validation (50% Bulgarian law) | **Not implemented** |

### Bulgarian Legal Requirement
Per Bulgarian Consumer Credit Act (Закон за потребителския кредит):
- ГПР must be displayed on every contract
- Maximum ГПР = 50%
- Must include ALL costs (fees, insurance, etc.) not just interest
- Calculation method: XIRR (EU Directive 2008/48/EC, Annex I)

---

## 33. Contract Template — Hardcoded Issues

### Location
`reports/loan_contract.xml` (~1400 lines)

### Hardcoded Company Info (lines 28-40)
- Specific company name baked in
- ЕИК `200735614` hardcoded
- Sofia address hardcoded
- Representative name hardcoded

### Guarantor Section (lines 62-76)
Static placeholder text:
```
ЕИК _______________
ЕГН _____________
лична карта № ___________
```
Not populated from any Odoo field.

### Other Hardcoded Elements
- Contract articles reference specific company name throughout
- Legal provisions reference specific company structure (ЕООД/ООД/АД)
- GDPR section names specific company as data controller

---

## 34. Translation Coverage (bg.po)

### Coverage: ~95%
- All field labels translated
- All status values translated
- All button labels translated
- All mail template subjects translated

### Key Translations
```
"Codebtor" → (not translated, stays "Codebtor")
"Codebtor Details" → "Подробности за съдлъжника"
"Loan Borrower" → (not translated)
"Person of contact" → (not translated)
```

### Missing Translations
- Role labels (`is_loan_borrower`, `is_person_of_contact`, `is_codebtor`) not fully translated
- Some wizard button labels

---

## 35. import_loans.py — Script Created

### Location
`/mnt/c/Odoo/LMS_21072025/import_loans.py` (27KB, 520 lines)

### Features
- **Config section:** URL, DB, user, password, TEST_MODE, Excel path, cutoff date
- **Template generation:** `python import_loans.py --template` creates `loan_import_template.xlsx`
- **19 Excel columns:** customer_egn, loan_type_name, app_date, approval_date, loan_amount, term, installment_type, interest_rate, start_date, installment_start_date, bank_name, bank_account, bank_branch_code, bank_swift, is_penalty, penalty_type, penalty_amount, penalty_percentage, paid_through_date
- **Validation:** EGN checksum, date consistency, required fields, numeric ranges
- **XML-RPC wrapper:** OdooRPC class with search/read/create/write/call methods
- **Lookups:** Customer by EGN, loan type by name, accounting config (accounts + journals)
- **Processing flow per row:**
  1. Validate → 2. Lookup customer → 3. Lookup loan type → 4. Lookup accounting →
  5. Create loan (draft) → 6. compute_installment() → 7. Write status=disbursement →
  8. action_disburse_loan() → 9. Post disbursement JE → 10. Write status=in_progress →
  11. For each past installment: create JE, set date, post
- **Test mode:** Validates everything, prints what would happen, creates nothing
- **Error handling:** Per-row try/except, summary at end (created/failed/skipped)

### Dependencies
- `openpyxl` (for Excel)
- `xmlrpc.client` (stdlib)
- `dateutil.relativedelta` (for test mode installment count estimation)

---

## 36. Documentation Files Created

| File | Size | Content |
|------|------|---------|
| `CLAUDE.md` | 6KB | Project context for all future Claude Code sessions |
| `PLAN.md` | 4KB | 8-phase development plan with checkboxes |
| `INVESTIGATION.md` | 15KB | Investigation findings (13 sections) |
| `SESSION_LOG.md` | This file | Comprehensive session log |

---

## 37. v1.0.8 Staging Differences

**Discovered:** 2026-03-05
**Location:** `C:\Odoo\Logos_LMS-staging\tk_loan_management` (v1.0.8)
**Compared against:** `C:\Odoo\LMS_21072025\tk_loan_management` (v1.0.6)

### Version Change
`1.0.6` → `1.0.8`

### New Files (3)

#### wizard/loan_payment.py (273 lines)
- **Model:** `loan.payment` (TransientModel)
- **Purpose:** Payment wizard for registering loan payments
- **Key methods:**
  - `default_get()` — pre-fills from active loan
  - `_compute_remain_amount()` — calculates remaining balance
  - `_compute_initial_fee()` — computes initial fee if applicable
  - `_onchange_initial_fee_payment()` — handles fee toggle
  - `action_register_payment()` — main action: allocates payment across categories
  - `_create_journal_entry()` — creates corresponding journal entry
- **Payment allocation order:** Interest → Penalty → Fee → Principal
- **Supports:** Initial fee payment handling, credit balance tracking

#### wizard/loan_payment_view.xml (54 lines)
- Form view for `loan.payment` wizard
- Fields: `amount`, `date`, `credit_balance`, `is_initial_fee_payment`, `initial_fee`, `remaining_installment_count`
- Button: "Register Payment" with confirm dialog

#### data/revised_instalment_schedule_mail.xml (183 lines)
- Email template `tk_loan_management.revised_installment_schedule`
- Notifies customer when schedule changes after prepayment
- Contains: loan amount, interest rate, term, disbursement date, recalculated installment table

### New Fields (7)

#### On `customer.loan`:
```
send_recalculate_inst_mail  Boolean     Flag: send revised schedule email
```

#### On `customer.loan.type`:
```
is_overdue_penalty_interest Boolean     "Apply overdue interest" toggle
od_penalty_interest         Float       "Overdue Interest" rate
```
With validation: `od_penalty_interest > 0` when enabled, reset to 0 on disable.

#### On `account.move`:
```
loan_line_id                M2O(customer.loan.lines)  Links JE to specific installment
is_initial_fee_journal      Boolean                    Marks initial fee journal entries
```

#### On `account.move.line`:
```
is_overdue_interest         Boolean     Default=False   Marks overdue interest lines
is_interest                 Boolean     Default=False   Marks interest lines
is_principal                Boolean     Default=False   Marks principal lines
is_fee                      Boolean     Default=False   Marks fee lines
```
These flags enable detailed tracking of what each journal entry line represents.

### New Methods (5)

#### On `customer.loan`:

**`action_recalculate_installment()` (lines 1619-1723)**
- Triggered after prepayment
- Validates credit balance > 0
- Removes all remaining unpaid installment lines
- Creates a prepayment line with journal entry (debit receivable, credit bank)
- Calculates new principal = old principal - prepayment amount
- Regenerates installment schedule for remaining term
- Sets `send_recalculate_inst_mail = True`

**`_generate_recalculated_installment()` (lines 1724-1804)**
- Helper for `action_recalculate_installment()`
- Generates new installment lines with recalculated EMI
- Handles holiday-aware date calculation
- Returns list of `(0, 0, vals)` commands for `loan_lines_ids`

**`action_send_recalculate_mail()` (lines 1806-1820)**
- Sends `revised_installment_schedule` mail template
- Clears `send_recalculate_inst_mail` flag

#### On `customer.loan.type`:

**`_check_overdue_penalty_interest()` (constraint)**
- Validates `od_penalty_interest > 0` when `is_overdue_penalty_interest = True`

**`_onchange_overdue_penalty_interest()` (onchange)**
- Resets `od_penalty_interest = 0` when toggle disabled

### Modified Methods (1)

#### `_calculate_emi()` — Signature Change
```python
# v1.0.6:
def _calculate_emi(self, loan_amount, interest_rate, term, installment_type):
    ...
    if self.is_grace_period:
        term -= self.grace_period

# v1.0.8:
def _calculate_emi(self, loan_amount, interest_rate, term, installment_type, is_grace_period):
    ...
    if is_grace_period:
        term -= self.grace_period
```
Grace period check is now parameter-driven instead of reading from `self`. This allows the method to be called from recalculation context where grace period should not apply.

### Modified Fields (1)

#### `customer.loan.type.product_id`
```python
# v1.0.6: no auto_join
product_id = fields.Many2one(..., index=True, ...)

# v1.0.8: added auto_join=True
product_id = fields.Many2one(..., auto_join=True, index=True, ...)
```
Performance optimization for SQL joins through the delegated product.

### Controllers (Present in v1.0.8, missing from v1.0.6 file listing)

| File | Lines | Purpose |
|------|-------|---------|
| `controllers/customer_portal_controller.py` | 722 | Customer portal: view loans, installments, docs, sign sanction letters |
| `controllers/lead_website_controler.py` | 226 | Website loan application form processing |
| `controllers/sanction_letter_controller.py` | 354 | Sanction letter signing flow (portal) |

> Note: These controllers may have existed in v1.0.6 but were not in the file listing of the original `LMS_21072025` directory. They are identical in both copies.

### Minor Cleanup
- `customer_loan_res_partner.py`: removed unused `import datetime` (line 4 in v1.0.6)
- `customer_loan_account_move.py`: removed unused import `from odoo.api import ValuesType, Self`

### Summary: What v1.0.8 Adds

| Feature | Impact |
|---------|--------|
| **Loan Prepayment** | Customers can make early payments; remaining schedule auto-recalculates |
| **Payment Wizard** | Structured payment entry with allocation across interest/penalty/fee/principal |
| **Revised Schedule Notification** | Email sent to customer after prepayment with new schedule |
| **Overdue Interest Config** | Loan types can now define overdue penalty interest rates |
| **JE Line Type Tracking** | Boolean flags on journal entry lines identify what each line represents |
| **Performance** | `auto_join=True` on loan type product delegation |

### Impact on Development Plan

- **Phase 3 (Loan Fixes):** Installment recalculation partially addressed by v1.0.8 prepayment feature, but manual editing of individual installment lines is still not possible
- **Phase 7 (Import Scripts):** `import_loans.py` was written against v1.0.6 method signatures — `_calculate_emi()` signature changed, but script calls `compute_installment()` via XML-RPC which calls `_calculate_emi()` internally, so **no script changes needed**
- **`loan.payment` wizard:** New wizard model needs to be added to `SESSION_LOG.md` model catalog (total now: 30 persistent + 9 wizards = 39 model classes)

---

## Session: Phase 2 Complete — 2026-03-10

### Phase 2 Deliverables (tested and working)

**`tk_loan_management_bg/models/partner_bg.py`**
- `company_registry` — EIK validation (9-digit Bulgarian checksum, two-pass algorithm)
- `bulstat` field + validation (same checksum algorithm)
- `manager_id` (МОЛ) — Many2one to individual partner
- `is_guarantor` Boolean role (Поръчител)
- `_check_personal_number` override — skips EGN/ID validation for `is_company=True`
- `_rec_names_search` extended with `personal_number` for dropdown search
- `_compute_display_name` override — shows EGN after name for individuals

**`tk_loan_management_bg/views/partner_bg_views.xml`**
- Company Information group (EIK, BULSTAT, МОЛ) — visible only when `is_company=True`
- Personal Information group hidden for companies via `invisible="is_company"`
- EGN, ID card, date_of_issuing — `required="not is_company"` + `invisible="is_company"`
- Labour Information group hidden for companies
- Family Details group hidden for companies
- `is_guarantor` checkbox added after `is_codebtor` in Roles section

**`tk_loan_management_bg/models/loan_bg.py`** (Phase 3 overlap, also complete)
- `represented_by` — company representative on loan (domain: contacts of customer)
- `codebtor_loan_ids` — M2M with domain `is_codebtor=True`
- `guarantor_ids` — M2M with domain `is_guarantor=True`

**`tk_loan_management_bg/views/loan_bg_views.xml`** (Phase 3 overlap, also complete)
- `represented_by` inserted before `phone` field on loan form
- New tab "Съдлъжници / Co-debtors" with `codebtor_loan_ids` as many2many_tags
- New tab "Поръчители / Guarantors" with `guarantor_ids` as many2many_tags
- Both tabs readonly after `confirm` status

### Remaining Phase 3 Item
- [ ] Editable installment grid (override readonly on `loan_lines_ids`)

### Next Phase
Phase 4: ГПР/XIRR calculation (Bulgarian legal requirement, max 50% per ZPK)
- Pure Python Newton-Raphson XIRR
- `gpr` computed field on `customer.loan`
- `total_cost_of_credit` and `total_amount_payable` computed fields
- Constraint: max 50%
- Display on loan form and contract report

---

## Session: Phase 3 Complete — 2026-03-10

### Bug Fix: represented_by field

**Problem:** Domain `[('parent_id', '=', customer_id)]` searched for Odoo child-contacts of
the company. МОЛ is a standalone partner with no `parent_id` link → empty dropdown always.

**Fix (`models/loan_bg.py`):**
- Domain changed to `[('is_company', '=', False)]` — any individual selectable
- Added `@api.onchange('customer_id')` → auto-fills `represented_by` from `customer_id.manager_id`
- Field clears when borrower switches to individual

**Fix (`views/loan_bg_views.xml`):**
- Added `invisible="not customer_id.is_company"` — field hidden for individual borrowers

---

### Feature: Guarantor and Co-debtor line tables

**Replaced** Many2many tag widgets with proper One2many line models so each row can carry
a percentage field and unlimited rows can be added.

**New models (`models/loan_bg.py`):**

| Model | Fields |
|-------|--------|
| `customer.loan.codebtor.line` | `loan_id` (cascade), `partner_id` (domain: `is_codebtor=True`), `guarantee_percentage` Float |
| `customer.loan.guarantor.line` | `loan_id` (cascade), `partner_id` (domain: `is_guarantor=True`), `guarantee_percentage` Float |

**Replaced fields on `customer.loan`:**
- `codebtor_loan_ids` (M2M) → `codebtor_line_ids` (O2M to `customer.loan.codebtor.line`)
- `guarantor_ids` (M2M) → `guarantor_line_ids` (O2M to `customer.loan.guarantor.line`)

**View (`views/loan_bg_views.xml`):**
- Tab "Съдлъжници": editable list with Partner + Share % columns
- Tab "Поръчители": editable list with Partner + Guarantee % columns
- Both tabs locked (`readonly`) after `confirm` status

**Security (`security/ir.model.access.csv`):**
- Full access (no group restriction) for both new models

**Upgrade issue fixed:** `options=` kwarg was mistakenly placed in Python field definitions
(it is a view XML attribute only). This caused a silent module load failure in Odoo 19,
leaving the old view with the removed `codebtor_loan_ids` field in the DB → frontend crash.
Removed the invalid kwarg and bumped version to `1.0.1` to force a clean re-upgrade.

---

### Phase 3 status
- All items complete and tested ✅
- Editable installment grid **postponed** — v1.0.8 prepayment wizard covers the main use case

### Next: Phase 4 — ГПР/XIRR
Legal requirement per ZPK чл. 19, ал. 4 (max 50%). Must appear on every contract.
- Pure Python Newton-Raphson XIRR in `models/loan_gpr.py`
- `gpr`, `total_cost_of_credit`, `total_amount_payable` computed fields on `customer.loan`
- Hard constraint: ValidationError if ГПР > 50%
- Display on loan form and contract report

---

## Session: Phase 4 Complete — 2026-03-10

### Feature: Financial Parameters

**New file: `tk_loan_management_bg/models/loan_gpr.py`**

New computed fields on `customer.loan`:

| Field | Type | Value (test loan 24% APR, 10 months) |
|-------|------|---------------------------------------|
| `eir_ifrs` | Float (10,6) | 2.012660 % — periodic EIR per IFRS 9 |
| `gpr` | Float (10,6) | 26.850392 % — annual ГПР/APRC |
| `total_cost_of_credit` | Monetary | total interest + all fees |
| `total_amount_payable` | Monetary | principal + total cost |

**Calculation logic (identical to Excel):**

```
EIR_IFRS = excel_irr(cashflows)  where:
    cashflows[0]   = −net_disbursed      (lender outflow, period 0)
    cashflows[1…n] = +total_instalment_i (lender inflow, equal periods)
    Result: PERIODIC rate (not annualised)

ГПР/APRC = excel_xirr(dates, amounts)  where:
    dates[0]   = disbursement_date,  amounts[0]   = −net_disbursed
    dates[1…n] = emi_date_i,         amounts[1…n] = +payment_i (P+I + fee)
    Result: ANNUAL rate, day fractions = (date − t₀).days / 365
```

Both use lender perspective (outflow negative, inflow positive).
`pyxirr` library used — matches Excel IRR() and XIRR() exactly.

**Disbursement date for XIRR t₀:**
`disbursement_date or approval_date or lines[0].emi_date`
(Using `start_date` = `installment_start_date` = first instalment date was the original bug causing inflated ГПР of 34.18% instead of 26.85%)

**New file: `tk_loan_management_bg/views/loan_gpr_views.xml`**
- "Financial Parameters" group added to Loan Evaluation tab, visible only when instalments exist
- `interest_rate` relabelled as "APR / Лихвен процент (%) — ANNLSD_AGRD_RT"
- Warning banner shown when ГПР > 50 %
- All four computed fields shown readonly

**Constraint:** `_check_gpr_max` — `ValidationError` if `gpr > 50` at status `confirmation` and beyond

**`requirements.txt`:** added `pyxirr`

---

### Bugs fixed during Phase 4 testing

| Bug | Cause | Fix |
|-----|-------|-----|
| ГПР = 0.0000 | `excel_xirr(amounts, dates)` — args swapped | `excel_xirr(dates, amounts)` |
| EIR = 27.013% instead of 2.012660% | Annualisation `(1+r)^n−1` applied — wrong for IFRS 9 periodic rate | Return `r_period * 100` directly |
| ГПР = 34.18% instead of 26.85% | `start_date` = first instalment date used as disbursement t₀; placed disbursement and instalment 1 on same date | Use `disbursement_date` as t₀ |
| 4 decimal places | `digits=(10,4)` | `digits=(10,6)` — reporting standard |

---

### Next: Phase 5 — Contract Template System
Go-live blocker: contract has hardcoded company info (wrong name, wrong EIK).
Must be dynamic before any Logos loan can be signed.

---

*End of session log.*

---

## Session 2026-03-11 — Phase 5 Complete + Currency Setup + Company Data

### Phase 5: Document System — COMPLETE (build passing)

Full document generation system implemented and deployed to staging. 5 build failures debugged:

| Build | Error | Fix |
|-------|-------|-----|
| 1 | `t-raw` removed in Odoo 17+ | Changed to `t-out` |
| 1 | `ref=` + `eval=` on same `<field>` | Removed redundant attribute |
| 2 | `base.paperformat_euro` not in Odoo 19 | Removed `paperformat_id` line |
| 2 | Ambiguous `//header` xpath | Changed to direct child `/header` |
| 3 | `<field name="is_active">True</field>` invalid | Changed to `eval="True"` |
| 3 | `noupdate` on `<odoo>` instead of `<data>` | Moved to `<data noupdate="1">` |
| 3 | `type="html"` on CDATA field → empty content | Removed `type="html"` attribute |
| Warning | Incomplete `@api.depends` on stored computed field | Added sub-fields `.name` |
| Warning | `readonly=True` on wizard Python field blocks ORM writes | Removed from Python, kept in view XML only |

**Base module "Loan Contract" suppressed** from gear/print menu:
```xml
<record id="tk_loan_management.loan_contract_report" model="ir.actions.report">
    <field name="binding_model_id" eval="False"/>
</record>
```

---

### Logos Company Data — Manually Entered

**Date:** 2026-03-11
**Environment:** Staging (Odoo.sh)
**Method:** Settings → Company (manual UI entry)

Logos company info (name, EIK, address, MOL, etc.) has been configured directly in Odoo staging.

**Impact on scripts:**
- `setup_logos.py` must **NOT overwrite** existing company data
- Pattern: read current value → skip if already set → write only if missing
- Company info section should be a "fill gaps" operation, not a full overwrite

---

### Currency Setup

**Decision:** EUR is the active company currency. BGN deactivated.
**Reason:** Bulgaria joins Eurozone 2026.
**Fixed rate:** 1.95583 (historical reference only — EUR is primary going forward).

`scripts/setup_logos.py` created with:
- Section 1: Currency — activate EUR, deactivate BGN, set `res.company.currency_id = EUR`
- Section 2: Loan types — 3 Logos products with all amounts in `€`
- `TEST_MODE = True` default; `--apply` flag to write

All loan type descriptions updated: `лв.` → `€`.

---

---

## Session: 2026-03-13 — ACCOUNTING_SPEC.md Analysis & Full Plan Update

### Files reviewed
- `ACCOUNTING_SPEC.md` (new authoritative accounting reference, v2.0)
- `CLAUDE.md`, `PLAN.md`, `INVESTIGATION.md` — all updated

### ACCOUNTING_SPEC.md — Summary

Entity: **НФИ** (non-bank financial institution, ЗКИ Art. 3a). Standard: **Bulgarian NAS**. Currency: **EUR** (post 01.01.2026).

#### Chart of accounts defined
- **Assets:** 262 (LT loans), 4110 (ST current), 4112 (overdue), 4113 (fees receivable), 4960 (accrued interest), 4961 (penalty receivable), 2991 (allowance/contra)
- **Cash:** 5030 (disbursements), 5031 (collections)
- **Liabilities:** 152/151 (funding), 4950 (deferred fees), 4532 (VAT)
- **Income:** 7210 (interest), 7220 (initial fees), 7230 (penalty), 7240 (admin fees), 7250 (loan taxes)
- **Expense:** 6210 (interest on funding), 6290 (provision)

#### 5 Journals required
LOAN-DISB, LOAN-COL, LOAN-OPS, LOAN-INV, LOAN-PEN

#### Key rules established
1. Loan asset = full principal always (fees never deducted from 4110/262)
2. Interest = accrual basis (DR 4960 / CR 7210 at installment date)
3. Penalty = **dual approach**: Approach A daily GL (4961/7230) + Approach B fresh calc at payment
4. `penalty_grace_days` configurable (default 0) — NEVER hardcode
5. Current penalty rate: **10.15% p.a.** (ECB main rate + 8pp, Постановление №426/2014)
6. FIFO payment order: **Penalty → Interest → Fee → Principal** (base module has wrong order)
7. Invoice mode: `invoice_receipt` (default) or `receipt_only` per config
8. LT/ST reclassification: monthly cron (262 → 4110)
9. Overdue reclassification: daily cron (4110 → 4112)
10. Provision for loan losses: DPD buckets (1-2% / 10-25% / 50% / 75% / 100%)

### Phase 3b — Regrouped into 8 implementation groups

| Group | Focus | Depends on | Priority |
|-------|-------|-----------|---------|
| A | Config settings + chart of accounts + journals | — | First (blocks all) |
| B | Disbursement: 4110+262 split, fee invoice | A | Pre go-live |
| C | Interest accrual cron (4960/7210) | A | Pre go-live |
| D | Penalty overhaul: dual approach, grace days, `waive_penalty` | A | Pre go-live |
| E | Payment wizard: FIFO fix, Approach B, receipt, invoice mode | C+D | Go-live |
| F | LT/ST reclassification + overdue status crons | B | Post go-live |
| G | Restructuring (decrease term) + pre-closure wizard | E | Post go-live |
| H | Provision for loan losses | F | Post go-live |

### Files updated
- **`PLAN.md`**: Phase 3b completely rewritten with GROUP A–H; Priority Order updated
- **`CLAUDE.md`**: Accounting reference section rewritten (chart of accounts, JE table, FIFO order, penalty rules, base module gaps); Remaining items updated to GROUP A–H; dev rules updated
- **`INVESTIGATION.md`**: Section 13 gap table updated with ✅ for completed phases; Section 14 added (9-point analysis with exact file:line references)
- **`SESSION_LOG.md`**: This entry

### Next steps (in order)
1. Implement **GROUP A** — `res.config.settings` extension + data files for COA + journals
2. Implement **GROUP B** — disbursement JE overhaul
3. Implement **GROUP C + D** — accrual + penalty crons
4. Write **`setup_generic.py`** (Phase 6) configuring journals and accounts via XML-RPC
5. Write **`import_contacts.py`** and refine **`import_loans.py`** (Phase 7)


---

## Session: 2026-03-13 (continued) — AnaCredit_CLAUDE.md Analysis & Full Project Overview

### Files reviewed
- `AnaCredit_CLAUDE.md` — standalone BNB AnaCredit generator reference (placed in project root)
- All project docs cross-checked for consistency

### AnaCredit_CLAUDE.md — Summary

The file documents `anacredit_generator_v3.0.py` (v3.1), a **standalone Python script** that is already working in production at `C:\BNB_Reports\Data_base\Anacredit Monthly\`.

**What it does:**
- Input: `CUCR_enhanced.csv` (manually prepared from Logos legacy software)
- Output: 10 BNB-required AnaCredit tables (Monthly M_FI_EA or Daily D_FI_EA)
- EUR transition: Bulgaria adopted EUR 01.01.2026; BGN legacy credits per-agent handled
- Key bug fixed this session: `int(NaN)` on `CUCR_EXP_NOM` (line ~932)

**Integration strategy decided:**
- Odoo stores AnaCredit fields on `customer.loan` → Export Wizard generates `CUCR_enhanced.csv` → fed into existing standalone generator → 10 BNB tables → BNB upload
- Generator script stays standalone — not reimplemented inside Odoo
- Integration is **post go-live** (generator already covers production needs)

### Phase 8 expanded into 3 groups

| Group | Scope |
|-------|-------|
| AC-1 | AnaCredit fields on `customer.loan` + `loan.type` + `res.config.settings` (5 new fields) |
| AC-2 | `CUCR_enhanced.csv` export wizard / XML-RPC script with all mapping logic |
| AC-3 | Workflow docs + BNB submission validation procedure |

### Full project overview as of 2026-03-13

#### COMPLETED (Phases 0–6-address + Phase 3 guarantor)
| Phase | Status | Key deliverable |
|-------|--------|----------------|
| 0 | ✅ Mostly done | Git, repo, docs (3 minor items open) |
| 1 | ✅ Done | Module skeleton |
| 2 | ✅ Done | EIK/BULSTAT/МОЛ/`is_guarantor`, EGN skip for companies |
| 3 | ✅ Done | `represented_by`, codebtor/guarantor tabs on loan |
| 4 | ✅ Done | ГПР/XIRR via pyxirr, 50% constraint |
| 5 | ✅ Done | Dynamic document templates, PDF+DOCX, 3 defaults |
| 6-address | ✅ Done | 28 oblasts + 5,256 ЕКАТТЕ settlements, partner settlement lookup |

#### IN SCOPE — pre go-live
| Phase | Group | Scope |
|-------|-------|-------|
| 3b | A | Config settings + chart of accounts + 5 journals |
| 3b | B | Disbursement: 4110+262 split, fee invoice |
| 3b | C | Interest accrual cron (4960/7210) |
| 3b | D | Penalty overhaul: dual approach, grace days, `waive_penalty` |
| 6 | — | Config scripts: `setup_generic.py`, `setup_logos.py` |
| 7 | — | Import scripts: `import_contacts.py`, `import_loans.py` |
| 3b | E | Payment wizard: FIFO fix, Approach B, receipt doc, invoice mode |

#### POST GO-LIVE
| Phase | Group | Scope |
|-------|-------|-------|
| 3b | F | LT/ST reclassification + overdue status crons |
| 3b | G | Decrease-term restructure + pre-closure wizard |
| 3b | H | Provision for loan losses (DPD buckets) |
| 8 | AC-1 | AnaCredit fields on loan + config |
| 8 | AC-2 | CUCR_enhanced.csv export |
| 8 | AC-3 | BNB submission workflow |

### Files updated this session
- `PLAN.md`: Phase 8 expanded into AC-1/AC-2/AC-3 with full field mapping table; Priority Order extended to 13 steps
- `CLAUDE.md`: AnaCredit section added (strategy, field mapping table, CUCR_EXP_NOM codes, new config fields); Remaining table updated with AC groups
- `INVESTIGATION.md`: Section 15 added — AnaCredit gap analysis (field-by-field status, computed logic, workflow)
- `SESSION_LOG.md`: This entry


---

## Session: 2026-03-14 — Penalty Architecture Decision

### Decision: Cash-basis penalty only. Account 4961 NOT used.

**Context:** Two findings reviewed — disbursement 4110+262 split and FIFO payment order.
During FIFO implementation review, penalty architecture corrected.

### What changed

**Removed:**
- Approach A daily GL cron (`DR 4961 / CR 7230`)
- 4961 (Penalty Receivable) account — removed from chart of accounts plan
- Approach A vs B reconciliation at payment time
- `penalty_accrued_informational` as a GL-posted field

**Kept / Added:**
- Daily cron: informational calc only → `penalty_accrued_informational` (Float, display only, zero JE)
- Payment wizard: **3 penalty options**:
  1. **Full** — `penalty_calculated_at_payment` (recalculated fresh on payment date)
  2. **Waived** — `exclude_penalty = True` → zero, no JE, reset informational field
  3. **Custom** — `penalty_custom_amount` (staff-editable negotiated amount)
- JE only on cash receipt: `DR 5031 / CR 7230`

### Fields on `customer.loan.lines`
| Field | Type | Purpose |
|-------|------|---------|
| `penalty_start_date` | Date | Computed: `emi_date + penalty_grace_days` |
| `penalty_accrued_informational` | Float | Daily calc — display only, no GL |
| `penalty_calculated_at_payment` | Float | Fresh calc when wizard opens |
| `penalty_custom_amount` | Float | Staff negotiated override |
| `waive_penalty` | Boolean | Permanent waiver flag |
| `paid_penalty` | Float | Running total actually received |

### Why this is right for Logos (small НФИ)
- Books stay clean until cash received ✅
- Client always sees accurate running penalty ✅
- Three options cover all real scenarios: pay full / waive / negotiate ✅
- One clean JE at payment, no reconciliation complexity ✅
- Simpler to implement and audit ✅

### Files updated
- `ACCOUNTING_SPEC.md`: Section 6 rewritten (cash basis), Section 7 FIFO table and 7B JE corrected
- `CLAUDE.md`: Penalty rules updated, JE table corrected, base module gaps updated
- `PLAN.md`: GROUP D rewritten (informational cron only), GROUP E penalty options updated



---

## Session: 2026-03-14 — GROUP A + GROUP B Implementation

### Overview
Full implementation of GROUP A (configuration foundation) and GROUP B (disbursement overhaul).
Module bumped from v1.0.11 → v1.0.13. All commits pushed to `staging` branch on GitHub.

---

### GROUP A — Configuration & Chart of Accounts (v1.0.12)

#### What was built

**`models/res_config_settings_bg.py`** (new file)
- `ResCompanyLMSBG` inherits `res.company` — 23 `lms_` prefixed fields:
  - Penalty: `lms_penalty_rate_annual` (10.15%), `lms_penalty_divisor` (360), `lms_penalty_grace_days` (0)
  - Invoice mode: `lms_fee_invoice_on_disburse` (Boolean)
  - Journals: `lms_disbursement_journal_id`, `lms_collection_journal_id`, `lms_operations_journal_id`, `lms_invoice_journal_id`
  - Asset accounts: `lms_lt_loan_account_id` (262), `lms_st_loan_account_id` (4110), `lms_overdue_loan_account_id` (4112), `lms_fees_receivable_account_id` (4113), `lms_accrued_interest_account_id` (4960), `lms_allowance_account_id` (2991)
  - Income accounts: `lms_interest_income_account_id` (7210), `lms_fee_income_account_id` (7220), `lms_penalty_income_account_id` (7230), `lms_early_repayment_income_account_id` (7240), `lms_other_income_account_id` (7250)
  - Expense account: `lms_provision_expense_account_id` (6290)
- `ResConfigSettingsLMSBG` inherits `res.config.settings` — all `related='company_id.lms_...'` fields with `readonly=False`

**`views/res_config_settings_bg_views.xml`** (new file)
- Inherits `base.res_config_settings_view_form`, inserts `<app>` block inside `//form`
- App name: "Loans (БГ)" — appears in Settings sidebar
- 5 `<block>` sections: Penalty, Journals, Receivable Accounts, Income Accounts, Expense Accounts
- Pattern follows `tk_loan_management`'s own settings view (same `<app>/<block>/<setting>` structure)

**`data/account_chart_bg.xml`** (new file, noupdate=1)
- 18 Bulgarian NAS accounts: 151, 152, 262, 2991, 4110, 4112, 4113, 4532, 4950, 4960, 5030, 5031, 7210, 7220, 7230, 7240, 7250, 6290

**`data/account_journals_bg.xml`** (new file, noupdate=1)
- 4 loan journals: LDISB (bank, default 5031), LCOL (bank, default 5031), LOPS (general), LINV (sale, default 7220)

**`models/loan_bg.py`** — `default_get()` added to `CustomerLoanBG`:
- Auto-populates 5 base accounting fields from `res.company.lms_*` on new loan creation:
  - `receivable_account_id` ← `lms_st_loan_account_id`
  - `interest_income_account_id` ← `lms_interest_income_account_id`
  - `bank_cash_account` ← `lms_disbursement_journal_id.default_account_id`
  - `journal_item_id` ← `lms_disbursement_journal_id`
  - `repayment_journal_item_id` ← `lms_collection_journal_id`

**`views/loan_bg_views.xml`** — two groups hidden via xpath:
- `group[@name='accounting_details']` → `invisible="1"`
- `group[@name='journal_details']` → `invisible="1"`

#### Key design decision: why inherit `res.company` not per-loan
Fields on `res.company` persist across settings save/discard cycles and across all loans.
Per-loan fields would require manual entry for every new loan — unacceptable for operations.

#### Bug fixed during implementation
First settings view attempt used wrong `inherit_id` (`account.res_config_settings_view_form`) and wrong xpath (`//div[hasclass('settings')]`). Fixed to `base.res_config_settings_view_form` + `//form` with `<app>` block — matching TechKhedut's own pattern.

#### Commits
- `361bed0` — models + data files (account chart + journals)
- `37198d7` — settings view fix (correct xpath + app pattern)
- `580c710` — hide base account fields; auto-populate via `default_get()`

---

### GROUP B — Disbursement Overhaul (v1.0.13)

#### What was built

**`models/loan_disburse_bg.py`** (new file) — `CustomerLoanDisburseBG` inherits `customer.loan`

**`_compute_st_lt_split(self)`:**
```python
ref_date = self.disbursement_date or fields.Date.today()
cutoff = ref_date + relativedelta(months=12)
st_amount = sum(line.installment_amount for line in self.loan_lines_ids
                if line.emi_date and line.emi_date <= cutoff and not line.display_type)
st_amount = min(max(st_amount, 0.0), self.loan_amount)
lt_amount = max(self.loan_amount - st_amount, 0.0)
```

**`action_disburse_loan(self)`** override:
1. Check BG accounts configured → if not, call `super()` and return (safe fallback)
2. Compute ST/LT split
3. Call `super()` → runs base validations, mail, status update, creates draft JE
4. If `super()` returned error → propagate it immediately
5. Replace draft JE lines: `(5,0,0)` deletes existing; adds DR 4110 (ST) + DR 262 (LT) / CR 5031
6. Post the corrected move with `move.action_post()`
7. If `lms_fee_invoice_on_disburse=True` and fee configured → call `_create_fee_invoice_bg()`

**`_create_fee_invoice_bg(self, fee_amount, fee_account, journal)`:**
- Creates `out_invoice` (customer invoice) on LINV journal
- Single line: `fee_amount → fee_income_acc (7220)`
- Calls `action_post()` immediately → status Paid

#### Journal Entry produced (after override)
```
DR  4110  Current portion (next 12-month principal)     [ST amount]
DR  262   Long-term remainder                           [LT amount]
    CR  5031  Bank — Loan account                       [loan_amount]
```

#### Edge cases handled
- `st_amount == 0` (all LT): only DR 262 line created
- `lt_amount == 0` (all ST, e.g. < 12-month loan): only DR 4110 line created
- `display_type` lines (section headers in schedule) excluded from sum
- `super()` error return propagated before any JE modification
- BG accounts not configured → falls back to base single-account JE

#### Commit
- `2d91157` — full GROUP B implementation

---

### Files updated this session
- `CLAUDE.md`: version → 1.0.13; Completed Accounting Groups table added; Remaining table updated; Custom Module Models table expanded
- `PLAN.md`: GROUP A marked ✅ COMPLETE with commits; GROUP B marked ✅ COMPLETE with implementation detail; Priority Order steps 1-2 marked ✅
- `SESSION_LOG.md`: this entry


---

## Session: 2026-03-14 (continued) — Payment FIFO Decision + GROUP C

### Payment FIFO Order — Architecture Decision

**Corrected from per-installment waterfall to global 4-round sweep.**

#### Old (wrong):
> Per installment: fully clear Penalty→Interest→Fee→Principal on installment #1,
> then move to installment #2, etc.

#### New (correct for Logos):
> Global sweep — each round clears one component across ALL installments (oldest first):
> - Round 1: ALL penalties (all installments)
> - Round 2: ALL fees (all installments)
> - Round 3: ALL interest (all installments)
> - Round 4: Principal FIFO (oldest first, partial OK)
> - Overpayment → `loan.credit_balance`

#### Why this matters
A partial payment that covers penalty + interest on installment #1 but not its principal
should still clear penalty on installment #2. The global sweep allows this; per-installment
waterfall would not. ЗПК Art. 35 mandates the priority ORDER, not per-installment isolation.

#### Files updated
- `ACCOUNTING_SPEC.md`: Section 7 fully rewritten (7.0 Algorithm, 7.1 Priority, 7.2 Code Structure, 7.3-7.7 examples)
- `CLAUDE.md`: Payment FIFO section updated to global sweep
- `INVESTIGATION.md`: Section 16 added with decision rationale and GROUP E impact

---

### GROUP C — Interest Accrual Cron (v1.0.14)

#### What was built

**`models/loan_accrual_bg.py`** (new file)

`CustomerLoanLineAccrualBG` inherits `customer.loan.lines`:
- `accrual_move_id` Many2one `account.move` (readonly, `ondelete='set null'`)
- `accrual_status` Selection: draft / posted / reversed (default: draft)

`CustomerLoanAccrualBG` inherits `customer.loan`:

`_cron_post_interest_accrual()`:
1. Reads `lms_accrued_interest_account_id` (4960), `lms_interest_income_account_id` (7210), `lms_operations_journal_id` from `res.company`
2. Logs warning + returns if any not configured (safe fallback)
3. Searches all `in_progress` loans
4. Per loan: filters lines where `emi_date == today AND accrual_status != 'posted' AND interest_amount > 0`
5. Per line: creates `account.move` with two lines (DR 4960 / CR 7210, `is_interest=True`), posts it, sets `accrual_move_id` + `accrual_status = 'posted'`
6. Per-line try/except: one failure doesn't block other loans
7. Logs total count at end

#### Journal Entry produced
```
DR  4960  Начислени лихви — {loan.name} / {inst_no}     [interest_amount]
    CR  7210  Приходи от лихви — {loan.name} / {inst_no} [interest_amount]
```
Fields on both lines: `partner_id`, `is_interest=True`, `customer_loan_id`, `loan_line_id`.

**`data/cron_accrual_bg.xml`** (new file):
- `ir.cron`: daily, unlimited runs (`numbercall=-1`), `priority=5` (runs before base penalty crons)
- Code: `model._cron_post_interest_accrual()`

#### Design notes
- Cron uses `priority=5` to run before base module penalty crons (priority=10 by default)
- `accrual_status` field allows future reversal logic (advance payment in GROUP E)
- `is_interest=True` flag on move lines reuses base module's existing tracking flag
- `noupdate=0` on cron so admin can adjust schedule without data reset

#### Files updated
- `CLAUDE.md`: GROUP C added to Completed Accounting Groups; version → 1.0.14
- `PLAN.md`: GROUP C marked ✅ COMPLETE; priority step 3 marked ✅
- `SESSION_LOG.md`: this entry

---

## Session: 2026-03-14 (continued) — GROUP D: Penalty System

### Overview
GROUP D implements the cash-basis penalty system. Decision confirmed: Account 4961 NOT used.
No daily GL entries. Informational display only.

### What was built

**`models/loan_penalty_bg.py`** — two classes:

1. `CustomerLoanLinePenaltyBG` (`_inherit = 'customer.loan.lines'`) — 6 new fields:
   - `penalty_start_date` — stored computed: `emi_date + lms_penalty_grace_days`; depends on `company_id.lms_penalty_grace_days`
   - `penalty_accrued_informational` — Float(16,2); updated daily by cron; display-only; zero GL
   - `penalty_calculated_at_payment` — Float(16,2); recalculated fresh when payment wizard opens
   - `penalty_custom_amount` — Float(16,2); staff-negotiated amount (Option 3 in wizard)
   - `waive_penalty` — Boolean; permanent waiver flag; resets informational to 0
   - `paid_penalty` — Float(16,2), readonly; running total of penalty cash received and posted

2. `CustomerLoanPenaltyBG` (`_inherit = 'customer.loan'`) — 3 methods:
   - `_cron_installment_due_penalty()` → no-op (overrides base GL-posting cron)
   - `_cron_loan_overdue_penalty()` → no-op (overrides base compound interest cron)
   - `_cron_update_penalty_informational()` → daily informational update:
     - `daily_rate = lms_penalty_rate_annual / 100 / lms_penalty_divisor`
     - For each overdue line (today > penalty_start_date, not waived, unpaid_base > 0):
       - `penalty_accrued_informational = unpaid_base × daily_rate × overdue_days`
     - Resets to 0 for waived or fully-cleared lines
     - Zero DR/CR anywhere. Account 4961 NOT used.

**`data/cron_penalty_bg.xml`** — `ir.cron` record:
- Model: `customer.loan`; method: `_cron_update_penalty_informational()`
- Daily, priority=7, unlimited runs, active=True

#### Files modified
- `models/__init__.py`: added `from . import loan_penalty_bg`
- `__manifest__.py`: added `data/cron_penalty_bg.xml`; version → 1.0.15
- `CLAUDE.md`: GROUP D added to Completed Accounting Groups; version → 1.0.15
- `PLAN.md`: GROUP D marked ✅ COMPLETE
- `SESSION_LOG.md`: this entry

---

## Session: 2026-03-14 (continued) — GROUP E: Payment Wizard Overhaul

### Overview
GROUP E replaces the base `loan.payment` wizard `action_register_payment()` with a
BG-correct global 4-round FIFO sweep and correct accounting.

### What was built

**`wizard/loan_payment_bg.py`** — `LoanPaymentBG(_inherit='loan.payment')`:

**New fields:**
- `penalty_option` Selection (`full`/`waived`/`custom`) — defaults `full`
- `penalty_custom_amount_wizard` Float — editable when option=`custom`
- `penalty_calculated_display` Float — computed on `date` + `customer_loan_id`; fresh penalty total to payment date

**`_compute_penalty_display()`:**
- Iterates overdue lines (skips waived, skips not-yet-overdue)
- `total = sum(max(0, calc - already_paid))` using `lms_penalty_rate_annual / lms_penalty_divisor`

**`action_register_payment()` override:**
- Delegates initial-fee payments unchanged to `super()`
- Falls back to base wizard if `lms_collection_journal_id` / `lms_accrued_interest_account_id` / `lms_st_loan_account_id` not set
- Global 4-round sweep (ЗПК Art. 35 priority):
  - Round 1 — ALL penalties (oldest first); `custom` mode consumes `penalty_custom_amount_wizard` greedily
  - Round 2 — ALL fees → 4113
  - Round 3 — ALL interest → 4960
  - Round 4 — Principal FIFO → 4112 (if `emi_date < payment_date`) or 4110
- Per installment: one `account.move` (all components bundled) → `action_post()`
  - Compatible with base `_compute_amount()` flag detection (`is_interest`, `is_fee`, `is_principal`, `is_overdue_interest`)
- Updates GROUP D stored fields `paid_penalty` + `penalty_accrued_informational` after JE post
- `waived` mode: sets `waive_penalty=True` + resets `penalty_accrued_informational=0` on all overdue lines
- Overpayment: `loan.credit_balance = remaining`

**`views/loan_payment_bg_views.xml`** — inherits `loan.payment.view.form`:
- xpath removes `readonly="1"` from `date` field
- Inserts after `credit_balance`: `penalty_calculated_display` (readonly), `penalty_option` (radio), `penalty_custom_amount_wizard` (hidden unless custom)

#### Files modified
- `wizard/__init__.py`: new file, imports `loan_payment_bg`
- `__init__.py`: added `from . import wizard`
- `__manifest__.py`: added `views/loan_payment_bg_views.xml`; version → 1.0.16
- `CLAUDE.md`: GROUP E added to Completed Accounting Groups; version → 1.0.16
- `PLAN.md`: GROUP E marked ✅ COMPLETE
- `SESSION_LOG.md`: this entry

---

## Session: 2026-03-15 — GROUP F, GROUP G, setup_logos.py, TK Integrity Check

### Overview
Four topics addressed in this session:
1. GROUP F — Reclassification & overdue status (built and committed)
2. GROUP G — Pre-closure wizard + decrease-term wizard (built and committed)
3. `scripts/setup_logos.py` — migrated from XML-RPC to JSON-RPC, env-var config
4. TechKhedut integrity verification (formal check, documented)

---

### GROUP F — Reclassification & Overdue Status (v1.0.17, commit `19ed298`)

**`models/loan_reclass_bg.py`** — two classes:

**`CustomerLoanLineReclassBG(_inherit='customer.loan.lines')`:**
- `days_overdue` Integer — stored computed, `@api.depends('emi_date')`, days since emi_date if unpaid
- `overdue_reclass_move_id` Many2one(`account.move`) — guards against duplicate daily reclassification JE
- `status` `selection_add=[('overdue','Overdue / Просрочено')]` with `ondelete={'overdue':'set default'}`
- `_compute_status()` override: calls `super()` then promotes `status='unpaid'` past-due lines to `'overdue'`

**`CustomerLoanReclassBG(_inherit='customer.loan')`:**
- `lt_reclass_move_id` Many2one(`account.move`) — tracks current monthly LT/ST reclassification move
- `_compute_lt_st_reclass_delta()`: `new_st_remaining` = principal for lines `emi_date ≤ today+12mo`; `orig_st_remaining` = principal for lines `emi_date ≤ disbursement_date+12mo`; delta = new − orig
- `_cron_reclassify_overdue()`: daily — for each overdue line without `overdue_reclass_move_id`, posts DR 4112 / CR 4110
- `_cron_reclassify_lt_st()`: monthly — reverses existing `lt_reclass_move_id` then reposts DR 4110 / CR 262 for the new delta amount

**`data/cron_reclass_bg.xml`:** Two `ir.cron` records (no `numbercall` field — removed in Odoo 17+):
- `cron_lms_overdue_reclass` — daily, priority 8
- `cron_lms_lt_st_reclass` — monthly, priority 9

#### Files modified
- `models/__init__.py`: added `from . import loan_reclass_bg`
- `__manifest__.py`: added `data/cron_reclass_bg.xml`; version → 1.0.17
- `CLAUDE.md`: GROUP F added to Completed Accounting Groups
- `PLAN.md`: GROUP F marked ✅ COMPLETE

---

### GROUP G — Pre-closure + Decrease Term (v1.0.18, commit `c76ac8f`)

**`wizard/pre_closure_bg.py`** — `PreClosureBG(_inherit='customer.pre.closure.wizard')`:

New fields: `closure_date` Date, `pre_closure_fee_pct` Float; computed Monetary display fields:
`remaining_principal_bg`, `remaining_interest_bg`, `penalty_total_bg`, `pre_closure_fee_bg`, `total_due_bg`

`action_pre_close_loan()` override:
1. Reverse future GROUP C accruals: finds `accrual_move_id` on lines where `accrual_status='posted'` and `emi_date > closure_date`; posts reversal + sets `accrual_status='reversed'`
2. Build settlement JE: DR 5031 (total) / CR per-line: 4112 (if `overdue_reclass_move_id`), 262 (if LT), 4110 (if ST current), 4960 (accrued interest), 7230 (penalty), 7240 (pre-closure fee)
3. Unlink future unpaid lines
4. Set `loan.status='pre_closure'`, `loan.loan_closure_date=closure_date`
5. Graceful fallback to `super()` if BG accounts not configured

**`wizard/loan_decrease_term_wizard.py`** — `LoanDecreaseTermWizard(_name='loan.decrease.term.wizard')`:

Fields: `loan_id`, `currency_id`, `restructure_date`, `remaining_principal` (computed), `current_installment` (computed), `new_term` (computed via formula), `next_installment_date`

`_compute_wizard_fields()`: N = `ceil(−ln(1 − monthly_rate×P/A) / ln(1+monthly_rate))` (spec §11C)

`action_decrease_term()`:
- Validates: no overdue unpaid installments
- Unlinks future lines from `next_installment_date`
- Generates N new amortisation lines with standard PMT schedule; last installment adjusted for rounding residual
- Adds section header line for audit trail

#### Files modified
- `wizard/__init__.py`: added imports for `pre_closure_bg`, `loan_decrease_term_wizard`
- `views/pre_closure_bg_views.xml`: new view — adds `closure_date` + `pre_closure_fee_pct`, replaces summary group
- `views/loan_decrease_term_views.xml`: new view — wizard form + action + loan form header button
- `security/ir.model.access.csv`: access rule for `loan.decrease.term.wizard`
- `__manifest__.py`: added view files, version → 1.0.18
- `PLAN.md`: GROUP G marked ✅ COMPLETE

---

### setup_logos.py — JSON-RPC migration (commit `1fef838`)

**File:** `scripts/setup_logos.py` (first commit — previously untracked)

Changes from prior draft:
- Replaced `xmlrpc.client.ServerProxy` with `requests.Session` + JSON-RPC
  - Auth: POST `/web/session/authenticate` → stores session cookie
  - ORM calls: POST `/web/dataset/call_kw`
- Hardcoded `ODOO_URL/ODOO_DB/ODOO_USER/ODOO_PASS` → `os.getenv()` with staging defaults
- `call()` and `write_or_log()` simplified — no longer pass `models`/`uid` as args (module-level `_session`)
- Content unchanged: `setup_currencies()` (EUR active, BGN inactive) + `setup_loan_types()` (3 Logos products)
- `TEST_MODE=True` default + `--apply` flag pattern kept

---

### TechKhedut Integrity Check (2026-03-15)

Formal verification that `tk_loan_management/` has not been modified.

| Check | Result |
|-------|--------|
| `git diff HEAD -- tk_loan_management/` | **Empty** |
| `git status tk_loan_management/` | `nothing to commit, working tree clean` |
| `grep -r "VitoshaBG\|Logos" tk_loan_management/` | **Zero matches** |

Phase 2 commit `4be8bfa` appears in `git log -- tk_loan_management/` because that is when
all TK files were **first added to git** — all insertions, no edits.

**Result: CLEAN ✅** — OPL-1 compliance intact. Documented in `INVESTIGATION.md` Section 17.

---

### Documentation updates (this session)
- `INVESTIGATION.md`: Section 17 — TechKhedut Integrity Check added
- `SESSION_LOG.md`: this entry
- `PLAN.md`: Phase 0 ✅, Phase 1 ✅, GROUP F ✅, GROUP G ✅, setup_logos.py ✅; commit refs fixed; priority order updated
- `STATUS_REPORT.md`: new file — full project status snapshot

---

## Session: 2026-03-15 (continued) — Business Rules: Date Immutability + Holiday Logic

### Overview
Defined and documented two critical business rules that govern installment date handling
across the entire system. No code written — documentation and specification only.

---

### Rule 1: Installment Date Immutability

**Decision:** `customer.loan.lines.emi_date` is permanently immutable once
`customer.loan.status = 'in_progress'`.

**Legal basis:**
- Signed contract references specific dates
- AnaCredit DPD reporting requires unchanged reference dates
- ЗПК penalty/interest calculations anchor to agreed schedule

**Technical enforcement specified:**
```python
def _write(self, vals):
    if 'emi_date' in vals:
        if not self.env.context.get('allow_annex_change'):
            if any(l.customer_loan_id.status == 'in_progress' for l in self):
                raise UserError("Датата на вноска не може да бъде променяна "
                                "след активиране на кредита.")
        else:
            if not self.env.user.has_group('tk_loan_management.department_manager'):
                raise UserError("Само мениджър може да променя дата по анекс.")
    return super()._write(vals)
```

**Exception — signed annex:** `context={'allow_annex_change': True}` + manager group + audit log.
**Exception — restructure/pre-closure:** Unlinks lines, creates NEW schedule. Original dates frozen.

**What is NOT an exception:**
- Holiday detection, weekend detection, any cron, any wizard, any script

---

### Rule 2: Holiday-Aware Date Generation (new loans only)

**Decision:**
1. System calculates installment date mathematically
2. If date is holiday/weekend → system **suggests** next business day
3. Loan officer **reviews and confirms** — human decision required
4. Officer may override suggestion
5. Date locked after disbursement

**System suggests. Human confirms. System never auto-applies.**

**Not affected by holiday logic:** existing in-progress loans, penalty/interest cron calculations.

---

### Rule 3: Holiday Coverage Specification (for setup_generic.py)

Bulgarian public holidays 2026–2035 in `resource.calendar.leaves`:
- 10 fixed national holidays per year (Jan 1, Mar 3, May 1, May 6, May 24, Sep 6, Sep 22, Dec 24, Dec 25, Dec 26)
- Orthodox Easter (4 days × 10 years) — auto-calculated
- Weekend compensation (КТ чл.154 ал.2) — auto-calculated per year
- Special 2026: Jan 2 — "Еднократен почивен — въвеждане EUR"

Annual check cron (`_cron_holiday_coverage_check`):
- Runs December 1st each year
- Finds latest date in `resource.calendar.leaves`
- If `max_year − current_year ≤ 2` → sends `mail.message` to admin
- Message links to `dv.parliament.bg` for government decrees

---

### Files updated (documentation only — no code)
- `CLAUDE.md`: New section "CRITICAL BUSINESS RULES" (date immutability + holiday logic + coverage spec)
- `ACCOUNTING_SPEC.md`: Rules 11–12 added to Section 15 summary; full Rule 15 and Rule 16 sections added
- `INVESTIGATION.md`: Section 18 (Core Business Rules — 18.1 immutability, 18.2 holiday logic, 18.3 scenario table)
- `PLAN.md`: Phase 6 `setup_generic.py` item expanded with holiday sub-tasks
- `STATUS_REPORT.md`: Business rules table added to completed section
- `SESSION_LOG.md`: this entry

---

## Session: 2026-03-15 (continued) — _adjust_due_date() Month-End Logic

### Decision: Jan 1 correction

Previous spec said "Jan 1 → move to December." This was WRONG.

**Corrected rule:** Jan 1 is NOT a special case. It is day 1 of a 31-day month.
`days_to_month_end = 30`. Not in last 3 days. → Move AFTER (next business day in January).
Jan installment stays in January. Moving to December would create two December installments — forbidden.

### Master rule established

**ONE installment per month — never cross month boundary in either direction.**

This supersedes any simple "next business day" approach.

### Direction algorithm (_adjust_due_date)

```
if days_to_month_end <= 2:          # last 3 days of month
    → move BEFORE (prev business day, same month)
elif moving AFTER would cross month:
    → move BEFORE (prev business day, same month)
else:
    → move AFTER (next business day, same month)
```

Safety guards: `UserError` if no business day found in month (extremely rare — only if
entire last week of month were holidays, practically impossible).

### Examples table (finalised)

| Original | Reason | Days to EOM | Direction | Result |
|----------|--------|-------------|-----------|--------|
| Jan 1 | Holiday | 30 | AFTER | Jan 2 (or next working) |
| Mar 3 Mon | Holiday | 28 | AFTER | Mar 4 Tue |
| May 1 Fri | Holiday | 30 | AFTER | May 4 Mon |
| May 24 Sun | Weekend+holiday | 7 | AFTER | May 25 Mon |
| Nov 30 Sat | Weekend | 0 | BEFORE | Nov 29 Fri |
| Dec 24 holiday | Holiday | 7 | AFTER | Dec 26 Fri (if Dec 25 also holiday) |
| Dec 29 Fri holiday | Holiday | 2 | BEFORE | Dec 28 Thu |
| Dec 30 Sun holiday | Weekend+holiday | 1 | BEFORE | Dec 28 Fri (skips Dec 29 if also off) |
| Dec 31 Sat | Weekend | 0 | BEFORE | Dec 30 Fri |

### Files updated
- `CLAUDE.md`: Holiday-Aware Date Generation section replaced with corrected algorithm,
  direction table, full example table, complete Python code for `_adjust_due_date()`,
  `_prev_business_day()`, `_is_non_working()`, `_get_bg_holidays()`, UI message template
- `ACCOUNTING_SPEC.md`: Rule 16 rewritten — master rule, direction table, Jan 1 correction,
  Dec 31 example, link to CLAUDE.md for full code
- `PLAN.md`: setup_generic.py sub-tasks expanded — Jan 1 clarification ✅,
  direction examples ✅, implementation of helper methods ⬜
- `SESSION_LOG.md`: this entry

---

## Session: 2026-03-15 (continued) — Dec 31 edge cases confirmed

Q: Dec 31 Sunday → Dec 29 Fri (Dec 30 Sat also weekend)
Q: Dec 31 Saturday → Dec 30 Fri
Both handled by existing `_adjust_due_date()` — `days_to_month_end = 0` → move BEFORE,
walk backward until working day. No special case needed.

Note: Easter four-day block (Апрелски пример Apr 27-30) also confirmed — all four
contractual dates resolve to same last business day (Apr 24 in example). Apr 27 takes
AFTER→fallback→BEFORE path; Apr 28-30 take BEFORE directly. Algorithm correct.

---

## Session: 2026-03-15 (continued) — setup_generic.py built

### Overview
`scripts/setup_generic.py` — complete generic Odoo configuration script.
JSON-RPC, env-var config, TEST_MODE=True default, --apply pattern.

### Section 1: Holidays (resource.calendar.leaves + public.holidays)

`build_holiday_list(years)` computes all entries per year:
- 10 fixed national holidays (КТ чл.154 ал.1)
- 4 Orthodox Easter days: Good Fri + Holy Sat + Easter Sun + Easter Mon
  - Algorithm: Julian calendar + 13 days → Gregorian. Verified 2025–2035.
- Special one-offs: Jan 2 2026 "Еднократен почивен ден — въвеждане на EUR"
- Weekend compensations (КТ чл.154 ал.2):
  - Saturday holiday → following Monday (if not already a holiday)
  - Sunday holiday → following Monday (if not already a holiday)
  - Easter Sat/Sun compensations correctly skipped (Mon already Easter Monday)

2026 output: 18 entries. Dec 26 Sat → Dec 28 Mon. May 24 Sun → May 25 Mon.
Sep 6 Sun → Sep 7 Mon. Apr 11 Sat comp skipped (Apr 13 = Easter Monday).

Populates BOTH:
- `resource.calendar.leaves` (calendar_id, date_from/to, time_type='leave')
  → used by our `_adjust_due_date()` / `_get_bg_holidays()`
- `public.holidays` (start_date, end_date, action_confirm())
  → used by base module `_get_valid_installment_date()`

Skip-if-exists logic prevents duplicates on re-run.

### Section 2: Penalty Settings (res.company)
Writes `lms_penalty_rate_annual`=0.1015, `lms_penalty_divisor`=365,
`lms_penalty_grace_days`=0 — skips each field if already set to non-zero.

### Section 3: Document Types (customer.document.type)
8 standard loan document types. Skip-if-exists.

### Files modified
- `scripts/setup_generic.py`: new file
- `PLAN.md`: setup_generic.py marked ✅ COMPLETE with sub-task detail
- `STATUS_REPORT.md`: scripts table updated
- `SESSION_LOG.md`: this entry

---

## Session: 2026-03-15 (continued) — Fix: @string xpath selector forbidden in Odoo 19

### Error
```
odoo.tools.convert.ParseError: while parsing pre_closure_bg_views.xml:9
View inheritance may not use attribute 'string' as a selector.
```

Occurred on install of `tk_loan_management_bg` — module failed to load.

### Root cause
`views/pre_closure_bg_views.xml` used `@string` attribute as xpath selector:
```xml
<xpath expr="//group[@string='Loan Details']" position="replace">
<xpath expr="//group[@string='Pre-Closure Details']" position="attributes">
```
Odoo 19 explicitly forbids `@string` as a view inheritance selector.

### Fix
Replaced with field-content predicates by reading the base wizard view to identify
a unique field inside each target group:

| Old (forbidden) | New (valid) |
|----------------|-------------|
| `//group[@string='Loan Details']` | `//group[.//field[@name='remaining_loan_principle_amount']]` |
| `//group[@string='Pre-Closure Details']` | `//group[.//field[@name='is_pre_closure_charge']]` |

Commit: `9a7dd46`

### Rule added to CLAUDE.md
New section "ODOO 19 — VIEW INHERITANCE RULES" with:
- Forbidden vs valid selector table
- Field-content predicate pattern
- Workflow: open base view → find unique field inside target group → use as predicate
