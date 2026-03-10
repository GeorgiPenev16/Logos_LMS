# -*- coding: utf-8 -*-
"""
Financial parameters for every loan (Phase 4).

Workflow:
  1. User sets interest_rate (= APR / ANNLSD_AGRD_RT) on the loan.
  2. compute_installment() generates the amortisation schedule.
  3. This module computes from that schedule:
       - EIR_IFRS  : Effective Interest Rate per IFRS 9
                     = Excel IRR(cash_flows) per period → annualised
       - ГПР / APRC: Annual Percentage Rate of Charge
                     = Excel XIRR(amounts, dates) on all cash flows incl. fees
       - total_cost_of_credit
       - total_amount_payable
  4. A constraint blocks confirmation if ГПР > 50 % (ZPK чл. 19, ал. 4).

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
        digits=(10, 4),
        help=(
            "Effective Interest Rate per IFRS 9.\n"
            "= Excel IRR(P+I cash flows) per period, annualised.\n"
            "Equals APR for a standard annuity with no upfront fees; "
            "rises when upfront fees are present."
        ),
    )

    gpr = fields.Float(
        string="ГПР / APRC (%)",
        compute='_compute_financial_rates',
        store=True,
        digits=(10, 4),
        help=(
            "Годишен Процент на Разходите (Annual Percentage Rate of Charge).\n"
            "= Excel XIRR(all cash flows, actual dates), "
            "including per-instalment fees and upfront fees.\n"
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
        'start_date',
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

            upfront       = loan._upfront_fees_amount()
            total_pni     = sum(l.total_installment_amount or 0.0 for l in lines)
            total_ln_fee  = sum(l.fee_amount or 0.0 for l in lines)

            loan.total_amount_payable = total_pni + total_ln_fee + upfront
            loan.total_cost_of_credit = loan.total_amount_payable - loan.loan_amount

            net = loan.loan_amount - upfront   # net amount received by borrower

            # ── EIR IFRS 9  =  Excel IRR  ────────────────────────────────
            # Cash flows: −net on day 0, then each P+I instalment (no fees,
            # per IFRS 9 amortised-cost definition).
            eir_cashflows = [-net] + [l.total_installment_amount or 0.0 for l in lines]
            loan.eir_ifrs = loan._calc_eir(eir_cashflows)

            # ── ГПР / APRC  =  Excel XIRR  ───────────────────────────────
            # All cash flows on actual calendar dates, incl. per-line fees.
            disburse_date = loan.start_date or lines[0].emi_date
            xirr_dates   = [disburse_date]  + [l.emi_date for l in lines]
            xirr_amounts = [net] + [
                -((l.total_installment_amount or 0.0) + (l.fee_amount or 0.0))
                for l in lines
            ]
            loan.gpr = loan._calc_gpr(xirr_dates, xirr_amounts)

    def _calc_eir(self, cashflows):
        """
        EIR = Excel IRR(cashflows) per period, annualised.

        cashflows : [−net_disbursed, instalment_1, instalment_2, …]
        """
        self.ensure_one()
        if not _PYXIRR_AVAILABLE:
            return 0.0
        try:
            r_period = excel_irr(cashflows)
            if r_period is None or r_period <= -1.0:
                return 0.0
            n = {'monthly': 12, 'quarterly': 4, 'yearly': 1}.get(
                self.installment_type, 12)
            return round(((1.0 + r_period) ** n - 1.0) * 100.0, 4)
        except Exception:
            return 0.0

    def _calc_gpr(self, dates, amounts):
        """
        ГПР = Excel XIRR(amounts, dates) × 100.

        dates   : [disbursement_date, emi_date_1, emi_date_2, …]
        amounts : [+net_disbursed,   −payment_1, −payment_2, …]
        """
        self.ensure_one()
        if not _PYXIRR_AVAILABLE:
            return 0.0
        try:
            r = excel_xirr(amounts, dates)
            if r is None:
                return 0.0
            return round(r * 100.0, 4)
        except Exception:
            return 0.0

    def _upfront_fees_amount(self):
        """
        Total upfront fees (monetary).

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
                    "ГПР %(rate).2f %% exceeds the legal maximum of 50 %% "
                    "(ZPK чл. 19, ал. 4).\n"
                    "Please reduce the interest rate or fees before confirming the loan."
                ) % {'rate': loan.gpr})
