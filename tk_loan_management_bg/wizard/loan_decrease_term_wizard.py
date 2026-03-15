# -*- coding: utf-8 -*-
"""
GROUP G — Decrease-Term Restructuring Wizard  (ЗПК §11C)

Keeps the same monthly installment amount but shortens the loan term.
Formula (spec §11C):
    monthly_rate = interest_rate / 100 / 12
    N = ceil(−log(1 − monthly_rate × remaining_principal / fixed_installment)
             / log(1 + monthly_rate))

Workflow:
1. Wizard opens from loan form button (status='in_progress' only)
2. Validates: no overdue unpaid installments (must be settled first)
3. Shows: remaining_principal, current installment, computed new N
4. On confirm:
   - Unlink future unpaid installment lines (emi_date > today)
   - Generate N new amortisation lines starting from next_installment_date
   - New schedule uses same interest_rate; principal_balance tracked per line
"""
import math
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LoanDecreaseTermWizard(models.TransientModel):
    """Decrease-term restructuring wizard."""
    _name = 'loan.decrease.term.wizard'
    _description = 'Loan Decrease Term Wizard / Намаляване срока на кредита'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        loan = self.env['customer.loan'].browse(self.env.context.get('active_id'))
        if loan:
            res['loan_id'] = loan.id
            res['currency_id'] = loan.currency_id.id
        return res

    loan_id = fields.Many2one(
        comodel_name='customer.loan',
        string='Loan / Кредит',
        required=True,
        readonly=True,
    )

    currency_id = fields.Many2one('res.currency', readonly=True)

    restructure_date = fields.Date(
        string='Restructure Date / Дата на преструктуриране',
        default=fields.Date.today,
        required=True,
    )

    remaining_principal = fields.Monetary(
        string='Remaining Principal / Остатъчна главница',
        currency_field='currency_id',
        compute='_compute_wizard_fields',
    )

    current_installment = fields.Monetary(
        string='Current Installment / Текуща вноска',
        currency_field='currency_id',
        compute='_compute_wizard_fields',
        help='Total monthly payment (principal + interest) from the existing schedule.',
    )

    new_term = fields.Integer(
        string='New Term (months) / Нов срок (месеци)',
        compute='_compute_wizard_fields',
        help='Computed from formula: N = ceil(−ln(1 − r×P/A) / ln(1+r))',
    )

    next_installment_date = fields.Date(
        string='First New Installment Date / Първа нова вноска',
        compute='_compute_wizard_fields',
    )

    @api.depends('loan_id', 'restructure_date')
    def _compute_wizard_fields(self):
        for rec in self:
            loan = rec.loan_id
            today = rec.restructure_date or fields.Date.today()

            if not loan:
                rec.remaining_principal = 0.0
                rec.current_installment = 0.0
                rec.new_term = 0
                rec.next_installment_date = False
                continue

            active_lines = loan.loan_lines_ids.filtered(lambda l: not l.display_type)
            future_lines = active_lines.filtered(
                lambda l: l.emi_date and l.emi_date > today
            ).sorted('emi_date')

            rem_p = sum(max(0.0, l.remaining_principal or 0.0) for l in active_lines)
            rec.remaining_principal = rem_p

            # Current installment = total_installment_amount of first future line
            first_future = future_lines[:1]
            fixed_pmt = first_future.total_installment_amount if first_future else 0.0
            rec.current_installment = fixed_pmt

            # Next installment date
            rec.next_installment_date = first_future.emi_date if first_future else False

            # Compute new N
            annual_rate = loan.interest_rate or 0.0
            monthly_rate = annual_rate / 100.0 / 12.0

            if monthly_rate > 0 and fixed_pmt > 0 and rem_p > 0:
                x = monthly_rate * rem_p / fixed_pmt
                if x < 1.0:
                    n_float = -math.log(1.0 - x) / math.log(1.0 + monthly_rate)
                    rec.new_term = math.ceil(n_float)
                else:
                    # Fixed payment too small to cover interest — cannot converge
                    rec.new_term = 0
            elif monthly_rate == 0 and fixed_pmt > 0 and rem_p > 0:
                # Zero-interest loan
                rec.new_term = math.ceil(rem_p / fixed_pmt)
            else:
                rec.new_term = 0

    def action_decrease_term(self):
        """Confirm: cancel future lines, generate N new amortisation lines."""
        self.ensure_one()
        loan = self.loan_id
        today = self.restructure_date or fields.Date.today()
        active_lines = loan.loan_lines_ids.filtered(lambda l: not l.display_type)

        # ── Validation ────────────────────────────────────────────────────
        overdue_unpaid = active_lines.filtered(
            lambda l: l.emi_date and l.emi_date < today and (l.remaining_amount or 0.0) > 0.01
        )
        if overdue_unpaid:
            raise ValidationError(_(
                'Please settle all overdue installments before restructuring. '
                'Overdue: %s'
            ) % ', '.join(overdue_unpaid.mapped('installments_no')))

        if self.new_term <= 0:
            raise ValidationError(_(
                'Cannot compute new term — the current installment amount (%.2f) '
                'is too small to cover monthly interest on remaining principal (%.2f). '
                'Use Decrease Installment instead.'
            ) % (self.current_installment, self.remaining_principal))

        if not self.next_installment_date:
            raise ValidationError(_('No future installments found — loan may already be settled.'))

        fixed_pmt = self.current_installment
        rem_p = self.remaining_principal
        N = self.new_term
        annual_rate = loan.interest_rate or 0.0
        monthly_rate = annual_rate / 100.0 / 12.0
        start_date = self.next_installment_date
        company = self.env.company

        # ── Cancel future unpaid lines ────────────────────────────────────
        future_lines = active_lines.filtered(
            lambda l: l.emi_date and l.emi_date >= start_date
        )
        future_lines.unlink()

        # ── Generate new amortisation schedule ────────────────────────────
        balance = rem_p
        for i in range(N):
            emi_date = start_date + relativedelta(months=i)
            interest = round(balance * monthly_rate, 2)
            if i < N - 1:
                principal = round(fixed_pmt - interest, 2)
            else:
                # Last installment: clear remaining balance exactly
                principal = round(balance, 2)
                fixed_pmt_last = principal + interest
            total = principal + interest
            balance = round(balance - principal, 2)

            self.env['customer.loan.lines'].create({
                'customer_loan_id': loan.id,
                'installments_no': f'R-{i + 1:03d}',
                'emi_date': emi_date,
                'installment_amount': principal,
                'interest_amount': interest,
                'total_installment_amount': total,
                'fee_amount': 0.0,
                'principal_balance': max(0.0, balance),
                'company_id': company.id,
            })

        # Add section header for visibility
        loan.loan_lines_ids = [(0, 0, {
            'display_type': 'line_section',
            'name': f'Restructured — decrease term to {N} months from {start_date} '
                    f'(rate {annual_rate}% p.a., installment {self.current_installment:.2f})',
        })]

        return {'type': 'ir.actions.act_window_close'}
