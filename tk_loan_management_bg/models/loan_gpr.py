# -*- coding: utf-8 -*-
"""
Financial parameters for every loan (Phase 4).

Workflow:
  1. User sets interest_rate (= APR / ANNLSD_AGRD_RT) on the loan.
  2. compute_installment() generates the amortisation schedule.
  3. This module computes from that schedule:
       - EIR_IFRS  : Effective Interest Rate per IFRS 9 (periodic IRR → annual)
       - ГПР / APRC: Annual Percentage Rate of Charge via XIRR on all cash flows
       - total_cost_of_credit
       - total_amount_payable
  4. A constraint blocks confirmation if ГПР > 50 % (ZPK чл. 19, ал. 4).
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# ── Pure-Python financial math (no external libraries) ──────────────────────

def _irr_newton(cashflows):
    """
    Periodic IRR via Newton-Raphson for equally-spaced cash flows.

    cashflows : [CF0, CF1, CF2, …]  (CF0 is negative = disbursement)
    Returns   : periodic rate (float) or None on failure.
    """
    rate = 0.01
    for _ in range(500):
        try:
            f  = sum(cf / (1.0 + rate) ** i for i, cf in enumerate(cashflows))
            df = sum(-i * cf / (1.0 + rate) ** (i + 1) for i, cf in enumerate(cashflows))
        except (OverflowError, ZeroDivisionError):
            return None
        if abs(df) < 1e-12:
            break
        new_rate = rate - f / df
        if new_rate <= -1.0:
            new_rate = -0.9999
        if abs(new_rate - rate) < 1e-10:
            return new_rate
        rate = new_rate
    return rate


def _xirr_newton(cashflows):
    """
    XIRR via Newton-Raphson for date-stamped cash flows.

    cashflows : [(date, amount), …]
                First entry must be the disbursement (positive).
                Subsequent entries are repayments (negative).
    Returns   : annual rate (float) or None on failure.
    """
    if not cashflows or len(cashflows) < 2:
        return None

    t0 = cashflows[0][0]

    def years(d):
        return (d - t0).days / 365.0

    for initial_guess in (0.10, 0.05, 0.20, 0.01, 0.30):
        rate = initial_guess
        for _ in range(500):
            try:
                f  = sum(cf / (1.0 + rate) ** years(d) for d, cf in cashflows)
                df = sum(
                    -years(d) * cf / (1.0 + rate) ** (years(d) + 1)
                    for d, cf in cashflows
                )
            except (OverflowError, ZeroDivisionError):
                break
            if abs(df) < 1e-12:
                break
            new_rate = rate - f / df
            if new_rate <= -1.0:
                new_rate = -0.9999
            if abs(new_rate - rate) < 1e-10:
                return new_rate
            rate = new_rate
        # Accept if residual is close enough relative to loan size
        try:
            residual = abs(sum(cf / (1.0 + rate) ** years(d) for d, cf in cashflows))
            if residual < 1.0:
                return rate
        except (OverflowError, ZeroDivisionError):
            continue
    return None


# ── Model ────────────────────────────────────────────────────────────────────

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
            "Effective Interest Rate per IFRS 9 — the periodic IRR of the "
            "principal+interest cash flows, annualised. "
            "Equals APR for a standard annuity with no upfront fees."
        ),
    )

    gpr = fields.Float(
        string="ГПР / APRC (%)",
        compute='_compute_financial_rates',
        store=True,
        digits=(10, 4),
        help=(
            "Годишен Процент на Разходите (Annual Percentage Rate of Charge). "
            "XIRR of all cash flows: disbursement net of upfront fees, "
            "all instalments including per-instalment fees. "
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

            upfront = loan._upfront_fees_amount()
            total_pni      = sum(l.total_installment_amount or 0.0 for l in lines)
            total_line_fee = sum(l.fee_amount or 0.0 for l in lines)

            loan.total_amount_payable  = total_pni + total_line_fee + upfront
            loan.total_cost_of_credit  = loan.total_amount_payable - loan.loan_amount

            # ── EIR IFRS 9 ──
            # Net disbursement = loan_amount minus upfront fees already deducted.
            # Cash flows: P+I instalments only (per-instalment fees excluded per IFRS 9).
            net = loan.loan_amount - upfront
            eir_flows = [-net] + [l.total_installment_amount or 0.0 for l in lines]
            r_periodic = _irr_newton(eir_flows)
            if r_periodic is not None and r_periodic > -1.0:
                n = {'monthly': 12, 'quarterly': 4, 'yearly': 1}.get(
                    loan.installment_type, 12)
                loan.eir_ifrs = round(((1.0 + r_periodic) ** n - 1.0) * 100.0, 4)
            else:
                loan.eir_ifrs = 0.0

            # ── ГПР / APRC (XIRR) ──
            # All cash flows on actual dates, including per-instalment fees.
            disburse_date = loan.start_date or lines[0].emi_date
            xirr_flows = [(disburse_date, net)]
            for line in lines:
                payment = (line.total_installment_amount or 0.0) + (line.fee_amount or 0.0)
                xirr_flows.append((line.emi_date, -payment))

            r_annual = _xirr_newton(xirr_flows)
            loan.gpr = round(r_annual * 100.0, 4) if r_annual is not None else 0.0

    def _upfront_fees_amount(self):
        """
        Return the total upfront fee amount (monetary) for this loan.

        - initial_fee_amount  : percentage of loan_amount (shown as % in view)
        - processing_fee      : fixed amount OR percentage of loan_amount
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
