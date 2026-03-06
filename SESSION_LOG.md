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

*End of session log.*
