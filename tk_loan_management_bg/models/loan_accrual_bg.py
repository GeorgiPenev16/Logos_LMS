# -*- coding: utf-8 -*-
"""
GROUP C — Interest Accrual Cron

Daily cron at 06:00: for each active loan, post one JE per installment
whose emi_date == today and has not yet been accrued:

    DR  4960  Начислени лихви по кредити / Accrued Interest Receivable
        CR  7210  Приходи от лихви по кредити / Interest Income

Accounts read from res.company lms_* settings — never hardcoded.
Skipped gracefully if accounts/journal not configured.

Fields added to customer.loan.lines:
    accrual_move_id   — Many2one account.move (the posted accrual entry)
    accrual_status    — Selection: draft / posted / reversed
"""
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class CustomerLoanLineAccrualBG(models.Model):
    """Extend installment lines with accrual tracking fields."""
    _inherit = 'customer.loan.lines'

    accrual_move_id = fields.Many2one(
        'account.move',
        string='Interest Accrual Entry / Запис за начислена лихва',
        readonly=True,
        ondelete='set null',
    )
    accrual_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('reversed', 'Reversed'),
        ],
        string='Accrual Status / Статус начисляване',
        default='draft',
        readonly=True,
    )


class CustomerLoanAccrualBG(models.Model):
    """Interest accrual cron — GROUP C."""
    _inherit = 'customer.loan'

    @api.model
    def _cron_post_interest_accrual(self):
        """Post DR 4960 / CR 7210 for every installment due today.

        Called daily at 06:00 via ir.cron (cron_accrual_bg.xml).
        Creates one account.move per installment line, posts it,
        and stores the reference on the line for reconciliation.
        """
        today = fields.Date.today()
        company = self.env.company

        accrued_acc = company.lms_accrued_interest_account_id
        interest_income_acc = company.lms_interest_income_account_id
        ops_journal = company.lms_operations_journal_id

        if not (accrued_acc and interest_income_acc and ops_journal):
            _logger.warning(
                'LMS interest accrual cron: accounts or journal not configured '
                'in Settings → Loans (БГ). Skipping.'
            )
            return

        loans = self.search([('status', '=', 'in_progress')])
        accrued_count = 0

        for loan in loans:
            # Lines due today, not yet accrued, with a non-zero interest component
            due_lines = loan.loan_lines_ids.filtered(
                lambda l: (
                    l.emi_date == today
                    and not l.display_type
                    and l.accrual_status != 'posted'
                    and (l.interest_amount or 0.0) > 0
                )
            )

            for line in due_lines:
                inst_label = line.installments_no or str(line.id)
                ref = _('Interest accrual — %(loan)s / %(inst)s') % {
                    'loan': loan.name,
                    'inst': inst_label,
                }
                try:
                    move = self.env['account.move'].create({
                        'journal_id': ops_journal.id,
                        'date': today,
                        'ref': ref,
                        'move_type': 'entry',
                        'customer_loan_id': loan.id,
                        'loan_line_id': line.id,
                        'line_ids': [
                            (0, 0, {
                                'partner_id': loan.customer_id.id,
                                'account_id': accrued_acc.id,
                                'name': ref,
                                'debit': line.interest_amount,
                                'credit': 0.0,
                                'is_interest': True,
                            }),
                            (0, 0, {
                                'partner_id': loan.customer_id.id,
                                'account_id': interest_income_acc.id,
                                'name': ref,
                                'debit': 0.0,
                                'credit': line.interest_amount,
                                'is_interest': True,
                            }),
                        ],
                    })
                    move.action_post()
                    line.accrual_move_id = move.id
                    line.accrual_status = 'posted'
                    accrued_count += 1

                except Exception as e:
                    _logger.error(
                        'LMS accrual failed for loan %s line %s: %s',
                        loan.name, inst_label, str(e)
                    )

        _logger.info('LMS interest accrual cron: %d entries posted for %s', accrued_count, today)
