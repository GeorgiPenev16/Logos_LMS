# -*- coding: utf-8 -*-
"""
Financial parameters for every loan (Phase 4).

Workflow:
  1. User sets interest_rate (= APR / ANNLSD_AGRD_RT) on the loan.
  2. compute_installment() generates the amortisation schedule.
  3. This module computes from that schedule:

       EIR_IFRS  (= Excel IRR)
       ─────────────────────────────────────────────────────────────────
       Cash flows (lender perspective, equal periods):
           period 0 : −disbursement_amount   (bank pays out)
           period 1…n: +total_instalment_i    (bank receives P+I, fees excluded per IFRS 9)
       Result: PERIODIC effective interest rate (e.g. 2.012660 % / month).
       No annualisation — IFRS 9 EIR is the per-period rate.

       ГПР / APRC  (= Excel XIRR)
       ─────────────────────────────────────────────────────────────────
       Cash flows (lender perspective, actual calendar dates):
           disbursement_date : −net_disbursed        (bank pays out, net of upfront fees)
           each emi_date     : +total_instalment_i   (bank receives P+I + per-line fee)
       Result: ANNUAL rate based on actual day fractions (days / 365).
       Maximum 50 % per Bulgarian ZPK чл. 19, ал. 4.

       Relationship:
           IRR gives the PERIODIC rate → compare to APR / number_of_periods.
           XIRR gives the ANNUAL rate  → compare to ГПР legal limit.
           Both use the same cash-flow sign convention; XIRR additionally
           uses real dates instead of period numbers.

  4. A constraint blocks confirmation if ГПР > 50 %.

Requires: pyxirr  (pip install pyxirr)
          Replicates Excel IRR() and XIRR() exactly.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

try:
    from pyxirr import irr as excel_irr, xirr as excel_xirr
    _PYXIRR_AVAILABLE = True
except ImportError:
    _PYXIRR_AVAILABLE = False


class CustomerLoanFinancial(models.Model):
    """Financial parameters — Phase 4."""

    _inherit = 'customer.loan'

    # Note: interest_rate (existing field) = APR = ANNLSD_AGRD_RT
    # It is the agreed nominal annual rate entered by the user and used
    # by compute_installment() to build the amortisation schedule.

    eir_ifrs = fields.Float(
        string="EIR IFRS 9 (%)",
        compute='_compute_financial_rates',
        store=True,
        digits=(10, 6),
        help=(
            "Effective Interest Rate per IFRS 9 — periodic rate per instalment period.\n"
            "= Excel IRR(cash flows) where:\n"
            "  period 0 : −disbursement (lender outflow)\n"
            "  period 1…n: +total_instalment (P+I, fees excluded per IFRS 9)\n\n"
            "For monthly instalments this is the monthly rate (e.g. 2.012660 %).\n"
            "For quarterly: quarterly rate.  For yearly: annual rate.\n"
            "Not annualised — this is the per-period EIR as defined in IFRS 9."
        ),
    )

    gpr = fields.Float(
        string="ГПР / APRC (%)",
        compute='_compute_financial_rates',
        store=True,
        digits=(10, 6),
        help=(
            "Годишен Процент на Разходите (Annual Percentage Rate of Charge).\n"
            "= Excel XIRR(cash flows, actual dates) where:\n"
            "  disbursement_date : −net_disbursed (lender outflow, net of upfront fees)\n"
            "  each emi_date     : +payment (P+I + per-instalment fee)\n\n"
            "Always annual, based on actual day fractions (days / 365).\n"
            "Identical logic to EIR but uses real dates instead of period numbers.\n"
            "Maximum 50 % per ZPK чл. 19, ал. 4."
        ),
    )

    total_cost_of_credit = fields.Monetary(
        string="Total Cost of Credit / Обща цена на кредита",
        compute='_compute_financial_rates',
        store=True,
        currency_field='currency_id',
        help="Total interest + all fees paid over the life of the loan.",
    )

    total_amount_payable = fields.Monetary(
        string="Total Amount Payable / Обща дължима сума",
        compute='_compute_financial_rates',
        store=True,
        currency_field='currency_id',
        help="Principal + total cost of credit.",
    )

    # ── Computation ──────────────────────────────────────────────────────────

    @api.depends(
        'loan_lines_ids.emi_date',
        'loan_lines_ids.total_installment_amount',
        'loan_lines_ids.fee_amount',
        'loan_amount',
        'disbursement_date',
        'approval_date',
        'installment_type',
        'is_initial_fee', 'initial_fee_amount',
        'is_processing_fee', 'processing_fee_type',
        'processing_fee_amount', 'processing_fee_percentage',
    )
    def _compute_financial_rates(self):
        for loan in self:
            lines = loan.loan_lines_ids.sorted('emi_date')

            if not lines or not loan.loan_amount:
                loan.eir_ifrs = 0.0
                loan.gpr = 0.0
                loan.total_cost_of_credit = 0.0
                loan.total_amount_payable = 0.0
                continue

            upfront      = loan._upfront_fees_amount()
            total_pni    = sum(l.total_installment_amount or 0.0 for l in lines)
            total_ln_fee = sum(l.fee_amount or 0.0 for l in lines)

            loan.total_amount_payable = total_pni + total_ln_fee + upfront
            loan.total_cost_of_credit = loan.total_amount_payable - loan.loan_amount

            # net = amount actually received by borrower (after upfront fees deducted)
            net = loan.loan_amount - upfront

            # ── EIR IFRS 9  =  Excel IRR  ────────────────────────────────
            # Lender perspective, equal periods (1, 2, 3 …):
            #   period 0   : −net  (bank pays out)
            #   period 1…n : +total_installment_amount  (bank receives P+I)
            #                fees excluded per IFRS 9 amortised-cost definition
            # Result: periodic rate (e.g. 2.012660 %/month for 24 % APR monthly)
            eir_cashflows = [-net] + [l.total_installment_amount or 0.0 for l in lines]
            loan.eir_ifrs = loan._calc_eir(eir_cashflows)

            # ── ГПР / APRC  =  Excel XIRR  ───────────────────────────────
            # Lender perspective, actual calendar dates:
            #   disbursement_date : −net  (bank pays out)
            #   each emi_date     : +payment  (bank receives P+I + per-line fee)
            # disbursement_date is the actual date money was transferred.
            # Fallback: approval_date (when interest starts accruing per schedule).
            disburse_date = loan.disbursement_date or loan.approval_date or lines[0].emi_date
            xirr_dates   = [disburse_date] + [l.emi_date for l in lines]
            xirr_amounts = [-net] + [
                (l.total_installment_amount or 0.0) + (l.fee_amount or 0.0)
                for l in lines
            ]
            loan.gpr = loan._calc_gpr(xirr_dates, xirr_amounts)

    def _calc_eir(self, cashflows):
        """
        EIR = Excel IRR(cashflows) — periodic rate, NOT annualised.

        cashflows : [−net_disbursed, instalment_1, instalment_2, …]
                    Lender perspective: outflow negative, inflows positive.
        Returns   : periodic rate as percentage (e.g. 2.012660 for 2.012660 %).
        """
        self.ensure_one()
        if not _PYXIRR_AVAILABLE:
            return 0.0
        try:
            r_period = excel_irr(cashflows)
            if r_period is None or r_period <= -1.0:
                return 0.0
            return round(r_period * 100.0, 6)
        except Exception:
            return 0.0

    def _calc_gpr(self, dates, amounts):
        """
        ГПР = Excel XIRR(dates, amounts) × 100 — annual rate.

        dates   : [disbursement_date, emi_date_1, emi_date_2, …]
        amounts : [−net_disbursed,   +payment_1, +payment_2, …]
                  Lender perspective: outflow negative, inflows positive.
                  Uses actual day fractions (days / 365) — identical logic
                  to IRR but with real dates instead of period numbers.
        Returns : annual rate as percentage (e.g. 26.850392 for 26.850392 %).
        """
        self.ensure_one()
        if not _PYXIRR_AVAILABLE:
            return 0.0
        try:
            r = excel_xirr(dates, amounts)
            if r is None:
                return 0.0
            return round(r * 100.0, 6)
        except Exception:
            return 0.0

    def _upfront_fees_amount(self):
        """
        Total upfront fees in monetary amount.

        - initial_fee_amount  : stored as % of loan_amount in the base module
        - processing_fee      : fixed monetary OR % of loan_amount
        """
        self.ensure_one()
        amount = 0.0
        if self.is_initial_fee:
            amount += (self.loan_amount or 0.0) * (self.initial_fee_amount or 0.0) / 100.0
        if self.is_processing_fee:
            if self.processing_fee_type == 'percentage':
                amount += (self.loan_amount or 0.0) * (self.processing_fee_percentage or 0.0) / 100.0
            else:
                amount += self.processing_fee_amount or 0.0
        return amount

    # ── Legal constraint ─────────────────────────────────────────────────────

    @api.constrains('gpr', 'status')
    def _check_gpr_max(self):
        """Block progression past dept_approval if ГПР > 50 % (ZPK чл. 19, ал. 4)."""
        blocked = {'confirmation', 'disbursement', 'in_progress',
                   'pre_closure', 'settlement', 'closure'}
        for loan in self:
            if loan.status in blocked and loan.gpr > 50.0:
                raise ValidationError(_(
                    "ГПР %(rate).6f %% exceeds the legal maximum of 50 %% "
                    "(ZPK чл. 19, ал. 4).\n"
                    "Please reduce the interest rate or fees before confirming the loan."
                ) % {'rate': loan.gpr})
