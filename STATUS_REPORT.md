# Logos LMS — Project Status Report
Date: 2026-03-15
Version: tk_loan_management_bg v1.0.18

---

## ✅ COMPLETED (all pre go-live accounting groups done)

### Infrastructure
- Git + SSH authentication
- GitHub repo `GeorgiPenev16/Logos_LMS` (branch: staging)
- Odoo.sh staging connected
- TechKhedut `tk_loan_management` v1.0.8 installed by Kaushik (commit `092e0e1`)
- Documentation system:
  `CLAUDE.md`, `PLAN.md`, `INVESTIGATION.md`,
  `SESSION_LOG.md`, `ACCOUNTING_SPEC.md`,
  `AnaCredit_CLAUDE.md`

### Module: tk_loan_management_bg

| Phase | Group | Feature | Commit | Version |
|-------|-------|---------|--------|---------|
| 1 | — | Module foundation + manifest | `4be8bfa` | 1.0.0 |
| 2 | — | Partner/contact: EGN, EIK/BULSTAT, МОЛ, EGN in dropdowns, company/individual separation | `4be8bfa` | 1.0.0 |
| 3 | — | Loan model: `represented_by`, codebtor/guarantor O2M line tables, generated documents | `48ac14d` | — |
| 4 | — | ГПР/XIRR via pyxirr; EIR IFRS9; ЗПК Art.19 50% cap | `993e2ca` | — |
| 5 | — | Document system: 3 templates, 26 placeholders, PDF + DOCX | `7a2d6cb` | — |
| 6 | — | Bulgarian address system: 28 oblasts, 5,256 settlements (ЕКАТТЕ), partner address auto-fill | `0cf951c` | — |
| 6 | **A** | `res.config.settings` extension (23 `lms_` fields), Settings UI tab, 18 NAS accounts, 4 journals | `361bed0` | 1.0.12 |
| 6 | **B** | Disbursement overhaul: `_compute_st_lt_split()`, DR 4110+262/CR 5031, fee invoice (7220) | `2d91157` | 1.0.13 |
| 6 | **C** | Interest accrual cron (daily 06:00): DR 4960/CR 7210 per installment on due date | `9852d79` | 1.0.14 |
| 6 | **D** | Penalty cash-basis: 6 fields on `customer.loan.lines`, daily informational cron (zero GL) | `cb349d2` | 1.0.15 |
| 6 | **E** | Payment wizard FIFO overhaul: Penalty→Fee→Interest→Principal, BG accounts, 3 penalty options | `e27f45f` | 1.0.16 |
| 6 | **F** | Reclassification: daily 4110→4112, monthly LT→ST delta, `days_overdue`, `status='overdue'` | `19ed298` | 1.0.17 |
| 6 | **G** | Pre-closure ЗПК wizard + decrease-term wizard (formula §11C) | `c76ac8f` | 1.0.18 |

### Scripts
| Script | Status | Notes |
|--------|--------|-------|
| `scripts/setup_logos.py` | ✅ committed `1fef838` | JSON-RPC, env vars, currencies + 3 loan types |
| `scripts/setup_generic.py` | ✅ committed | Holidays 2026–2035 (both models), penalty settings, doc types |
| `scripts/import_contacts.py` | ⬜ not started | Borrowers/guarantors from Excel |
| `import_loans.py` (root) | ⬜ draft exists | Loan migration — needs validation |

### Business rules documented
| Rule | Status | Where |
|------|--------|-------|
| Installment date immutability after disbursement | ✅ documented | CLAUDE.md, ACCOUNTING_SPEC.md Rule 15, INVESTIGATION.md §18.1 |
| Holiday-aware schedule (suggest only, officer confirms) | ✅ documented | CLAUDE.md, ACCOUNTING_SPEC.md Rule 16, INVESTIGATION.md §18.2 |
| Annual holiday coverage check cron | ✅ spec written | CLAUDE.md |
| setup_generic.py — 10-year holiday data 2026–2035 | ✅ implemented | `resource.calendar.leaves` + `public.holidays` |

### TechKhedut integrity
✅ VERIFIED CLEAN (2026-03-15) — zero modifications, OPL-1 compliance intact.
See `INVESTIGATION.md` Section 17.

---

## 📋 PRE GO-LIVE (must complete before client go-live)

| # | Item | Phase | Notes |
|---|------|-------|-------|
| 1 | `scripts/setup_generic.py` | 6 | Journals, document types, public holidays |
| 2 | `scripts/import_contacts.py` | 7 | Company borrowers (ЕИК) + individuals (ЕГН) |
| 3 | `import_loans.py` validate + refine | 7 | Backdated loans + paid installments |
| 4 | Run imports on staging | 7 | Test with Logos data |
| 5 | User acceptance testing | Testing | Client sign-off required |
| 6 | Git branches: staging → production | Infra | Odoo.sh production deploy |

---

## 📋 POST GO-LIVE (planned)

| # | Item | Group | Notes |
|---|------|-------|-------|
| 1 | Provision for loan losses | **H** | DPD buckets, DR 6290/CR 2991 |
| 2 | AnaCredit fields on `customer.loan` | AC-1 | `anacredit_jud_dues`, `anacredit_tot_offbal`, agent id |
| 3 | CUCR_enhanced.csv export wizard | AC-2 | Feeds standalone `anacredit_generator_v3.0.py` |
| 4 | BNB submission workflow docs | AC-3 | Validate against known-good samples |
| 5 | Deferred fee amortisation cron | B | DR 4950/CR 7220 monthly (currently skipped) |
| 6 | Payment receipt document | E | Per `invoice_mode` config |
| 7 | Streets database | Address | Source TBD |
| 8 | Bulgarian translations review | i18n | Improve `bg.po` coverage |
| 9 | Finance Hold Bulgaria multi-company | Client | Separate Odoo instance |

---

## ⚠️ KNOWN DECISIONS PENDING

| Question | Impact | Who decides |
|----------|--------|-------------|
| Fee income account (7220 or 7240?) | GROUP E journals | Logos accountant |
| Penalty grace days (0 default OK?) | GROUP D config | Logos management |
| Invoice mode (`invoice_receipt` / `receipt_only`) | GROUP E | Logos management |
| Fee recognition (`immediate` / `amortised`) | GROUP B — deferred fee cron | Logos accountant |
| Decrease-installment restructure workflow | Base covers it — confirm OK | Logos management |

---

## 🏗️ ARCHITECTURE SUMMARY

```
Base:    tk_loan_management v1.0.8 (TechKhedut)
         NEVER modified — OPL-1 compliant ✅
         Integrity verified 2026-03-15

Custom:  tk_loan_management_bg v1.0.18 (VitoshaBG)
         All changes via Odoo _inherit only
         Groups A–G complete

Hosting: Odoo.sh Europe (staging)
Database: Logos staging (test data only)
Currency: EUR (BGN inactive — Eurozone 2026)
Standard: Bulgarian NAS, НФИ entity type
```

### Key accounting entries (implemented)

| Event | DR | CR | Group |
|-------|----|----|-------|
| Disbursement | 4110 (ST) + 262 (LT) | 5031 | B |
| Interest accrual | 4960 | 7210 | C |
| Payment — penalty | 5031 | 7230 | E |
| Payment — fee | 5031 | 4113 | E |
| Payment — interest | 5031 | 4960 | E |
| Payment — principal (current) | 5031 | 4110 | E |
| Payment — principal (overdue) | 5031 | 4112 | E |
| Overdue reclassification | 4112 | 4110 | F |
| LT→ST reclassification | 4110 | 262 | F |
| Pre-closure settlement | 5031 | 4110+4112+262+4960+7230+7240 | G |

### Authority documents
| File | Purpose |
|------|---------|
| `ACCOUNTING_SPEC.md` | Authoritative accounting rules — read before any accounting code |
| `AnaCredit_CLAUDE.md` | BNB reporting spec — standalone generator + Odoo integration plan |
| `CLAUDE.md` | Architecture rules, model reference, completed groups |
| `PLAN.md` | All phases with completion markers |
| `INVESTIGATION.md` | TechKhedut deep-dive + gap analysis + integrity check |
| `SESSION_LOG.md` | Full session history with file-level detail |

---

*Generated: 2026-03-15 | VitoshaBG EOOD | tk_loan_management_bg v1.0.18*
