# -*- coding: utf-8 -*-
"""
GROUP F — Reclassification & Overdue Status

Two crons + status/days_overdue fields:

1. CustomerLoanLineReclassBG — extends customer.loan.lines:
   - status: adds 'overdue' to selection; _compute_status override sets it
     when emi_date < today AND remaining_amount > 0
   - days_overdue: computed Integer (today - emi_date), stored
   - overdue_reclass_move_id: tracks the 4110 → 4112 reclassification JE

2. CustomerLoanReclassBG — extends customer.loan:
   - lt_reclass_move_id: tracks the monthly 262 → 4110 reclassification JE
   - _cron_reclassify_overdue()  daily  07:00 → DR 4112 / CR 4110 per overdue line
   - _cron_reclassify_lt_st()   monthly 1st, 07:00 → DR 4110 / CR 262 (delta)

Monthly LT/ST formula:
    reclass_delta = new_st_remaining − original_st_remaining
    new_st_remaining  = remaining_principal for lines with emi_date ≤ today + 12 months
    orig_st_remaining = remaining_principal for lines with emi_date ≤ disbursement_date + 12 months
    (positive → DR 4110 / CR 262; should only be positive as LT matures into ST)
"""
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


# ── Installment line extensions ───────────────────────────────────────────────

class CustomerLoanLineReclassBG(models.Model):
    """Adds overdue status + days_overdue + reclassification tracking."""
    _inherit = 'customer.loan.lines'

    # Extend base status with 'overdue'
    status = fields.Selection(
        selection_add=[('overdue', 'Overdue / Просрочено')],
        ondelete={'overdue': 'set default'},
    )

    days_overdue = fields.Integer(
        string='Days Overdue / Просрочени дни',
        compute='_compute_days_overdue',
        store=True,
        help='Number of days past the installment due date. 0 if not overdue.',
    )

    overdue_reclass_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Overdue Reclass JE / Преосчетоводяване просрочие',
        readonly=True,
        ondelete='set null',
        help='DR 4112 / CR 4110 journal entry posted when this line first became overdue.',
    )

    # ── days_overdue ──────────────────────────────────────────────────────

    @api.depends('emi_date')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for line in self:
            if line.emi_date and line.emi_date < today:
                line.days_overdue = (today - line.emi_date).days
            else:
                line.days_overdue = 0

    # ── status: extend base to set 'overdue' ──────────────────────────────

    @api.depends('remaining_amount', 'total_installment_amount', 'emi_date')
    def _compute_status(self):
        """Override: after base sets paid/partial/unpaid, promote unpaid past-due to overdue."""
        super()._compute_status()
        today = fields.Date.today()
        for rec in self:
            if rec.status == 'unpaid' and rec.emi_date and rec.emi_date < today:
                rec.status = 'overdue'


# ── Loan-level reclassification crons ────────────────────────────────────────

class CustomerLoanReclassBG(models.Model):
    """Monthly LT/ST reclassification cron + daily overdue reclassification cron."""
    _inherit = 'customer.loan'

    lt_reclass_move_id = fields.Many2one(
        comodel_name='account.move',
        string='LT/ST Reclass JE / Преосчетоводяване ДС→КС',
        readonly=True,
        ondelete='set null',
        help='Last posted 262→4110 reclassification entry. Reversed and reposted monthly.',
    )

    # ── Monthly LT/ST reclassification ───────────────────────────────────

    def _compute_lt_st_reclass_delta(self):
        """Return amount to move from 262 → 4110 since disbursement.

        delta = new_st_remaining − original_st_remaining
          new_st_remaining  = remaining_principal for lines emi_date ≤ today + 12 months
          orig_st_remaining = remaining_principal for lines emi_date ≤ disbursement_date + 12 months

        Positive: DR 4110 / CR 262 (LT matures into ST)
        Negative: reverse (unusual, defensive only)
        """
        self.ensure_one()
        today = fields.Date.today()
        cutoff_new = today + relativedelta(months=12)
        cutoff_orig = (self.disbursement_date or today) + relativedelta(months=12)

        new_st = 0.0
        orig_st = 0.0
        for line in self.loan_lines_ids:
            if line.display_type:
                continue
            rem = line.remaining_principal or 0.0
            if rem <= 0:
                continue
            if line.emi_date and line.emi_date <= cutoff_new:
                new_st += rem
            if line.emi_date and line.emi_date <= cutoff_orig:
                orig_st += rem

        return round(new_st - orig_st, 2)

    @api.model
    def _cron_reclassify_lt_st(self):
        """Monthly cron (1st of month, 07:00): reverse previous JE, post fresh delta.

        DR 4110  Вземания по кредити (current)
            CR 262   Предоставени дългосрочни заеми (LT)
        """
        company = self.env.company
        st_acc = company.lms_st_loan_account_id    # 4110
        lt_acc = company.lms_lt_loan_account_id    # 262
        ops_journal = company.lms_operations_journal_id

        if not (st_acc and lt_acc and ops_journal):
            _logger.warning(
                'LMS LT/ST reclass cron: lms_st_loan_account_id / lms_lt_loan_account_id / '
                'lms_operations_journal_id not configured — skipping.')
            return

        today = fields.Date.today()
        loans = self.search([('status', '=', 'in_progress')])
        posted = 0

        for loan in loans:
            try:
                # Reverse previous reclassification JE (if any)
                prev = loan.lt_reclass_move_id
                if prev and prev.state == 'posted':
                    reversal = prev._reverse_moves(
                        default_values_list=[{
                            'date': today,
                            'ref': f'{loan.name} — LT/ST reclass reversal {today}',
                            'journal_id': ops_journal.id,
                        }],
                        cancel=False,
                    )
                    reversal.action_post()
                    loan.lt_reclass_move_id = False

                delta = loan._compute_lt_st_reclass_delta()

                if abs(delta) < 0.01:
                    continue  # nothing to move

                if delta > 0:
                    # Normal: LT matures → DR 4110 / CR 262
                    debit_acc, credit_acc = st_acc, lt_acc
                else:
                    # Defensive: reverse direction (overpayment edge case)
                    debit_acc, credit_acc = lt_acc, st_acc
                    delta = abs(delta)

                move = self.env['account.move'].create({
                    'journal_id': ops_journal.id,
                    'date': today,
                    'ref': f'{loan.name} — LT/ST reclassification {today}',
                    'move_type': 'entry',
                    'customer_loan_id': loan.id,
                    'line_ids': [
                        (0, 0, {
                            'partner_id': loan.customer_id.id,
                            'account_id': debit_acc.id,
                            'name': f'LT→ST reclass {today}',
                            'debit': delta,
                            'credit': 0.0,
                        }),
                        (0, 0, {
                            'partner_id': loan.customer_id.id,
                            'account_id': credit_acc.id,
                            'name': f'LT→ST reclass {today}',
                            'debit': 0.0,
                            'credit': delta,
                        }),
                    ],
                })
                move.action_post()
                loan.lt_reclass_move_id = move.id
                posted += 1

            except Exception as e:
                _logger.error('LMS LT/ST reclass cron: loan %s failed — %s', loan.name, e)
                continue

        _logger.info('LMS LT/ST reclass cron: %d loans reclassified for %s', posted, today)

    # ── Daily overdue reclassification ────────────────────────────────────

    @api.model
    def _cron_reclassify_overdue(self):
        """Daily cron (07:00): for newly overdue lines post DR 4112 / CR 4110.

        Only fires once per line (overdue_reclass_move_id guards re-entry).
        Partial lines (status='partial') are also reclassified — remaining_principal
        is used so 4112 reflects the unpaid balance.
        """
        company = self.env.company
        overdue_acc = company.lms_overdue_loan_account_id  # 4112
        st_acc = company.lms_st_loan_account_id            # 4110
        col_journal = company.lms_collection_journal_id

        if not (overdue_acc and st_acc and col_journal):
            _logger.warning(
                'LMS overdue reclass cron: lms_overdue_loan_account_id / '
                'lms_st_loan_account_id / lms_collection_journal_id not configured — skipping.')
            return

        today = fields.Date.today()
        loans = self.search([('status', '=', 'in_progress')])
        posted = 0

        for loan in loans:
            for line in loan.loan_lines_ids:
                if line.display_type:
                    continue
                # Already reclassified
                if line.overdue_reclass_move_id:
                    continue
                # Not overdue
                if not line.emi_date or line.emi_date >= today:
                    continue
                # Nothing unpaid
                remaining_principal = line.remaining_principal or 0.0
                if remaining_principal <= 0.01:
                    continue

                try:
                    move = self.env['account.move'].create({
                        'journal_id': col_journal.id,
                        'date': today,
                        'ref': f'{loan.name} — overdue reclass {line.installments_no} {today}',
                        'move_type': 'entry',
                        'customer_loan_id': loan.id,
                        'loan_line_id': line.id,
                        'line_ids': [
                            (0, 0, {
                                'partner_id': loan.customer_id.id,
                                'account_id': overdue_acc.id,
                                'name': f'Overdue principal {line.installments_no}',
                                'debit': remaining_principal,
                                'credit': 0.0,
                            }),
                            (0, 0, {
                                'partner_id': loan.customer_id.id,
                                'account_id': st_acc.id,
                                'name': f'Overdue principal {line.installments_no}',
                                'debit': 0.0,
                                'credit': remaining_principal,
                            }),
                        ],
                    })
                    move.action_post()
                    line.overdue_reclass_move_id = move.id
                    posted += 1

                except Exception as e:
                    _logger.error(
                        'LMS overdue reclass cron: loan %s line %s failed — %s',
                        loan.name, line.installments_no, e)
                    continue

        _logger.info('LMS overdue reclass cron: %d lines reclassified for %s', posted, today)
