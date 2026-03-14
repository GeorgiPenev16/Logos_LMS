# -*- coding: utf-8 -*-
"""
GROUP E — Payment Wizard Overhaul (BG Accounting)

Overrides loan.payment with:
- Global 4-round FIFO sweep: Penalty → Fee → Interest → Principal  (ЗПК Art. 35)
- Correct BG accounts: 4960 (accrued interest), 4113 (fees), 4110/4112 (principal), 7230 (penalty)
- Unlocked payment date (view override in loan_payment_bg_views.xml)
- 3 penalty options: full / waived / custom
- One JE per installment (all components bundled) — compatible with base _compute_amount()
- Graceful fallback to base wizard if BG accounts not configured in Settings

Decision 2026-03-14: cash-basis penalty only. Account 4961 NOT used.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class LoanPaymentBG(models.TransientModel):
    """BG payment wizard — extends base loan.payment."""

    _inherit = 'loan.payment'

    # ── Penalty option ────────────────────────────────────────────────────
    penalty_option = fields.Selection(
        selection=[
            ('full', 'Full Penalty / Пълна наказателна лихва'),
            ('waived', 'Waive Penalty / Опрости наказателна лихва'),
            ('custom', 'Custom Amount / Договорена сума'),
        ],
        string='Penalty Option / Опция наказателна лихва',
        default='full',
    )

    penalty_custom_amount_wizard = fields.Monetary(
        string='Custom Penalty / Договорена наказателна лихва',
        currency_field='currency_id',
        default=0.0,
        help='Staff-negotiated penalty. Used only when Penalty Option = Custom.',
    )

    penalty_calculated_display = fields.Monetary(
        string='Calculated Penalty / Изчислена наказателна лихва',
        currency_field='currency_id',
        compute='_compute_penalty_display',
        help='Fresh penalty total to the selected payment date across all overdue installments.',
    )

    # ── Computed penalty display (refreshes when date changes) ───────────

    @api.depends('date', 'customer_loan_id')
    def _compute_penalty_display(self):
        for rec in self:
            total = 0.0
            loan = rec.customer_loan_id
            payment_date = rec.date or fields.Date.today()
            if not loan:
                rec.penalty_calculated_display = 0.0
                continue
            company = loan.company_id
            rate_annual = company.lms_penalty_rate_annual or 0.0
            divisor = company.lms_penalty_divisor or 360
            daily_rate = rate_annual / 100.0 / divisor if rate_annual else 0.0
            for line in loan.loan_lines_ids:
                if line.display_type or line.waive_penalty:
                    continue
                start = line.penalty_start_date
                if not start or payment_date <= start:
                    continue
                unpaid = (line.remaining_principal or 0.0) + (line.remaining_interest or 0.0)
                if unpaid <= 0:
                    continue
                overdue_days = (payment_date - start).days
                already_paid = line.paid_penalty or 0.0
                calc = round(unpaid * daily_rate * overdue_days, 2)
                total += max(0.0, calc - already_paid)
            rec.penalty_calculated_display = total

    # ── Main payment action ───────────────────────────────────────────────

    def action_register_payment(self):
        """Global 4-round sweep with BG accounts. Falls back to base if unconfigured."""
        self.ensure_one()

        # Delegate initial-fee payments unchanged to base
        if self.is_initial_fee_payment:
            return super().action_register_payment()

        loan = self.customer_loan_id
        payment_date = self.date or fields.Date.today()
        company = loan.company_id

        # ── Account / journal lookups ──────────────────────────────────────
        col_journal = company.lms_collection_journal_id
        bank_acc = col_journal.default_account_id if col_journal else None
        accrued_int_acc = company.lms_accrued_interest_account_id   # 4960
        fees_recv_acc = company.lms_fees_receivable_account_id      # 4113
        st_loan_acc = company.lms_st_loan_account_id                # 4110
        overdue_acc = company.lms_overdue_loan_account_id           # 4112
        pen_income_acc = company.lms_penalty_income_account_id      # 7230

        if not (col_journal and bank_acc and accrued_int_acc and st_loan_acc):
            _logger.warning(
                'LMS BG payment: collection journal or core accounts not configured '
                '— falling back to base payment wizard.')
            return super().action_register_payment()

        # ── Sweep preparation ──────────────────────────────────────────────
        remaining = self.amount + (self.credit_balance or 0.0)
        if remaining <= 0:
            raise ValidationError(_('Payment amount must be greater than zero.'))

        installments = loan.loan_lines_ids.filtered(
            lambda l: not l.display_type and l.remaining_amount > 0.0
        ).sorted('emi_date')

        # Snapshot penalty due per installment (before any JEs change computed fields)
        rate_annual = company.lms_penalty_rate_annual or 0.0
        divisor = company.lms_penalty_divisor or 360
        daily_rate = rate_annual / 100.0 / divisor if rate_annual else 0.0

        pen_snap = {}
        for inst in installments:
            if inst.waive_penalty or self.penalty_option == 'waived':
                pen_snap[inst.id] = 0.0
                continue
            start = inst.penalty_start_date
            if not start or payment_date <= start:
                pen_snap[inst.id] = 0.0
                continue
            unpaid = (inst.remaining_principal or 0.0) + (inst.remaining_interest or 0.0)
            if unpaid <= 0:
                pen_snap[inst.id] = 0.0
                continue
            overdue_days = (payment_date - start).days
            calculated = round(unpaid * daily_rate * overdue_days, 2)
            already_paid = inst.paid_penalty or 0.0
            pen_snap[inst.id] = max(0.0, calculated - already_paid)

        # Per-installment allocation
        alloc = {
            inst.id: {'penalty': 0.0, 'fee': 0.0, 'interest': 0.0, 'principal': 0.0}
            for inst in installments
        }

        # ── Round 1: ALL penalties ─────────────────────────────────────────
        if self.penalty_option == 'custom':
            custom_rem = max(0.0, self.penalty_custom_amount_wizard or 0.0)
            for inst in installments:
                if remaining <= 0 or custom_rem <= 0:
                    break
                pen_due = pen_snap.get(inst.id, 0.0)
                if pen_due <= 0:
                    continue
                pay = min(custom_rem, remaining, pen_due)
                alloc[inst.id]['penalty'] = pay
                remaining -= pay
                custom_rem -= pay
        else:
            for inst in installments:
                if remaining <= 0:
                    break
                pen_due = pen_snap.get(inst.id, 0.0)
                if pen_due <= 0:
                    continue
                pay = min(pen_due, remaining)
                alloc[inst.id]['penalty'] = pay
                remaining -= pay

        # ── Round 2: ALL fees ──────────────────────────────────────────────
        for inst in installments:
            if remaining <= 0:
                break
            fee_due = max(0.0, (inst.fee_amount or 0.0) - (inst.paid_fee or 0.0))
            if fee_due <= 0:
                continue
            pay = min(fee_due, remaining)
            alloc[inst.id]['fee'] = pay
            remaining -= pay

        # ── Round 3: ALL interest ──────────────────────────────────────────
        for inst in installments:
            if remaining <= 0:
                break
            int_due = max(0.0, (inst.interest_amount or 0.0) - (inst.paid_interest or 0.0))
            if int_due <= 0:
                continue
            pay = min(int_due, remaining)
            alloc[inst.id]['interest'] = pay
            remaining -= pay

        # ── Round 4: Principal FIFO ────────────────────────────────────────
        for inst in installments:
            if remaining <= 0:
                break
            princ_due = max(0.0, (inst.installment_amount or 0.0) - (inst.paid_principal or 0.0))
            if princ_due <= 0:
                continue
            pay = min(princ_due, remaining)
            alloc[inst.id]['principal'] = pay
            remaining -= pay

        # ── Post one JE per installment ────────────────────────────────────
        partner = loan.customer_id
        company_partner = loan.env.company.partner_id
        ref_base = f'{loan.name} — payment {payment_date}'

        for inst in installments:
            a = alloc[inst.id]
            total_inst = a['penalty'] + a['fee'] + a['interest'] + a['principal']
            if total_inst <= 0:
                continue

            move_lines = [(0, 0, {
                'partner_id': company_partner.id,
                'account_id': bank_acc.id,
                'name': ref_base,
                'debit': total_inst,
                'credit': 0.0,
            })]

            if a['penalty'] > 0:
                acc_pen = pen_income_acc if pen_income_acc else accrued_int_acc
                move_lines.append((0, 0, {
                    'partner_id': partner.id,
                    'account_id': acc_pen.id,
                    'name': _('Penalty / Наказателна лихва'),
                    'is_overdue_interest': True,
                    'debit': 0.0,
                    'credit': a['penalty'],
                }))

            if a['fee'] > 0:
                acc_fee = fees_recv_acc if fees_recv_acc else accrued_int_acc
                move_lines.append((0, 0, {
                    'partner_id': partner.id,
                    'account_id': acc_fee.id,
                    'name': _('Fee / Такса'),
                    'is_fee': True,
                    'debit': 0.0,
                    'credit': a['fee'],
                }))

            if a['interest'] > 0:
                move_lines.append((0, 0, {
                    'partner_id': partner.id,
                    'account_id': accrued_int_acc.id,
                    'name': _('Interest / Лихва'),
                    'is_interest': True,
                    'debit': 0.0,
                    'credit': a['interest'],
                }))

            if a['principal'] > 0:
                is_overdue = bool(inst.emi_date and inst.emi_date < payment_date)
                acc_princ = (overdue_acc if (is_overdue and overdue_acc) else st_loan_acc)
                move_lines.append((0, 0, {
                    'partner_id': partner.id,
                    'account_id': acc_princ.id,
                    'name': _('Principal / Главница'),
                    'is_principal': True,
                    'debit': 0.0,
                    'credit': a['principal'],
                }))

            move = self.env['account.move'].create({
                'journal_id': col_journal.id,
                'date': payment_date,
                'ref': f'{ref_base} — {inst.installments_no}',
                'move_type': 'entry',
                'customer_loan_id': loan.id,
                'loan_line_id': inst.id,
                'line_ids': move_lines,
            })
            move.action_post()

            # Update GROUP D stored penalty fields
            if a['penalty'] > 0:
                inst.paid_penalty = (inst.paid_penalty or 0.0) + a['penalty']
                inst.penalty_accrued_informational = max(
                    0.0, (inst.penalty_accrued_informational or 0.0) - a['penalty'])

        # ── Handle waived penalty across all installments ──────────────────
        if self.penalty_option == 'waived':
            for inst in installments:
                if not inst.waive_penalty:
                    inst.waive_penalty = True
                inst.penalty_accrued_informational = 0.0

        # ── Overpayment → credit balance ───────────────────────────────────
        loan.credit_balance = remaining if remaining > 0 else 0.0

        _logger.info(
            'LMS BG payment posted: loan=%s, date=%s, amount=%.2f, credit_balance=%.2f',
            loan.name, payment_date, self.amount, loan.credit_balance)
