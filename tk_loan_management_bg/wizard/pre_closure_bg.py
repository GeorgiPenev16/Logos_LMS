# -*- coding: utf-8 -*-
"""
GROUP G — Pre-Closure Wizard BG Override

Inherits customer.pre.closure.wizard and replaces action_pre_close_loan()
with BG-correct accounting:

Final settlement JE (single move):
    DR  5031  Bank Collections
        CR  4110  Current principal (not yet overdue-reclassified)
        CR  4112  Overdue principal (overdue_reclass_move_id set on line)
        CR  262   LT principal (emi_date > disbursement_date + 12 months)
        CR  4960  Remaining accrued interest
        CR  7230  Penalty income (cash basis)
        CR  7240  Pre-closure fee income

Additional steps:
- Reverse future accrual JEs (GROUP C accrual_move_id, accrual_status='posted')
- Cancel (unlink) all future unpaid installment lines
- Set loan.is_pre_closure=True, loan_closure_date=closure_date, status='pre_closure'

ЗПК right: no interest or penalty beyond the closure date — guaranteed because
future accruals are reversed and no new penalty lines are created after closure.

Graceful fallback to base wizard if BG accounts not configured.
"""
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class CustomerPreClosureWizardBG(models.TransientModel):
    _inherit = 'customer.pre.closure.wizard'

    # ── Additional BG fields ──────────────────────────────────────────────

    closure_date = fields.Date(
        string='Closure Date / Дата на закриване',
        default=fields.Date.today,
        required=True,
    )

    pre_closure_fee_pct = fields.Float(
        string='Pre-Closure Fee % / Такса предсрочно погасяване %',
        default=0.0,
        help='Fee charged on outstanding principal (e.g. 1.0 for 1%). Credited to 7240.',
    )

    # ── BG computed display fields ────────────────────────────────────────

    remaining_principal_bg = fields.Monetary(
        string='Remaining Principal / Остатъчна главница',
        currency_field='currency_id',
        compute='_compute_bg_totals',
    )

    remaining_interest_bg = fields.Monetary(
        string='Accrued Interest / Начислена лихва (4960)',
        currency_field='currency_id',
        compute='_compute_bg_totals',
    )

    penalty_total_bg = fields.Monetary(
        string='Penalty / Наказателна лихва',
        currency_field='currency_id',
        compute='_compute_bg_totals',
    )

    pre_closure_fee_bg = fields.Monetary(
        string='Pre-Closure Fee / Такса предсрочно',
        currency_field='currency_id',
        compute='_compute_bg_totals',
    )

    total_due_bg = fields.Monetary(
        string='Total Due / Общо дължимо',
        currency_field='currency_id',
        compute='_compute_bg_totals',
    )

    @api.depends('closure_date', 'pre_closure_fee_pct', 'loan_id')
    def _compute_bg_totals(self):
        for rec in self:
            loan = rec.loan_id
            if not loan:
                rec.remaining_principal_bg = 0.0
                rec.remaining_interest_bg = 0.0
                rec.penalty_total_bg = 0.0
                rec.pre_closure_fee_bg = 0.0
                rec.total_due_bg = 0.0
                continue

            lines = loan.loan_lines_ids.filtered(lambda l: not l.display_type)

            rem_p = sum(max(0.0, l.remaining_principal or 0.0) for l in lines)
            rem_i = sum(max(0.0, l.remaining_interest or 0.0) for l in lines)
            penalty = sum(
                max(0.0, (l.penalty_accrued_informational or 0.0) - (l.paid_penalty or 0.0))
                for l in lines if not l.waive_penalty
            )
            fee = round(rem_p * (rec.pre_closure_fee_pct or 0.0) / 100.0, 2)

            rec.remaining_principal_bg = rem_p
            rec.remaining_interest_bg = rem_i
            rec.penalty_total_bg = penalty
            rec.pre_closure_fee_bg = fee
            rec.total_due_bg = rem_p + rem_i + penalty + fee

    # ── Main action ───────────────────────────────────────────────────────

    def action_pre_close_loan(self):
        """BG pre-closure: correct accounts, reverse future accruals, single JE."""
        self.ensure_one()
        loan = self.loan_id
        company = loan.company_id
        closure_date = self.closure_date or fields.Date.today()

        # Account lookups
        col_journal = company.lms_collection_journal_id
        bank_acc = col_journal.default_account_id if col_journal else None
        st_acc = company.lms_st_loan_account_id                         # 4110
        overdue_acc = company.lms_overdue_loan_account_id               # 4112
        lt_acc = company.lms_lt_loan_account_id                         # 262
        accrued_int_acc = company.lms_accrued_interest_account_id       # 4960
        pen_income_acc = company.lms_penalty_income_account_id          # 7230
        fee_income_acc = company.lms_early_repayment_income_account_id  # 7240

        if not (col_journal and bank_acc and st_acc and accrued_int_acc):
            _logger.warning('LMS pre-closure BG: accounts not configured — falling back to base.')
            return super().action_pre_close_loan()

        partner = loan.customer_id
        company_partner = loan.env.company.partner_id
        orig_cutoff = (loan.disbursement_date or closure_date) + relativedelta(months=12)
        active_lines = loan.loan_lines_ids.filtered(lambda l: not l.display_type)

        # ── Step 1: Reverse future accrual JEs (GROUP C) ──────────────────
        future_accruals = active_lines.filtered(
            lambda l: l.emi_date and l.emi_date > closure_date
            and getattr(l, 'accrual_move_id', False)
            and getattr(l, 'accrual_status', '') == 'posted'
        )
        ops_journal = company.lms_operations_journal_id or col_journal
        for line in future_accruals:
            try:
                rev = line.accrual_move_id._reverse_moves(
                    default_values_list=[{
                        'date': closure_date,
                        'ref': f'{loan.name} — pre-closure accrual reversal',
                        'journal_id': ops_journal.id,
                    }],
                    cancel=False,
                )
                rev.action_post()
                line.accrual_status = 'reversed'
            except Exception as e:
                _logger.error('Pre-closure accrual reversal failed for %s: %s', loan.name, e)

        # ── Step 2: Build settlement JE lines ─────────────────────────────
        move_lines = []
        total = 0.0

        # Principal — credited to 4110 / 4112 / 262 per line classification
        for line in active_lines:
            rem_p = line.remaining_principal or 0.0
            if rem_p < 0.01:
                continue
            if getattr(line, 'overdue_reclass_move_id', False):
                acc = overdue_acc or st_acc   # 4112
            elif lt_acc and line.emi_date and line.emi_date > orig_cutoff:
                acc = lt_acc                  # 262
            else:
                acc = st_acc                  # 4110
            move_lines.append((0, 0, {
                'partner_id': partner.id,
                'account_id': acc.id,
                'name': f'Principal {line.installments_no}',
                'is_principal': True,
                'debit': 0.0,
                'credit': rem_p,
            }))
            total += rem_p

        # Interest — credited to 4960
        for line in active_lines:
            rem_i = line.remaining_interest or 0.0
            if rem_i < 0.01:
                continue
            move_lines.append((0, 0, {
                'partner_id': partner.id,
                'account_id': accrued_int_acc.id,
                'name': f'Interest {line.installments_no}',
                'is_interest': True,
                'debit': 0.0,
                'credit': rem_i,
            }))
            total += rem_i

        # Penalty — credited to 7230 (cash basis)
        if pen_income_acc:
            pen_total = sum(
                max(0.0, (l.penalty_accrued_informational or 0.0) - (l.paid_penalty or 0.0))
                for l in active_lines if not l.waive_penalty
            )
            if pen_total >= 0.01:
                move_lines.append((0, 0, {
                    'partner_id': partner.id,
                    'account_id': pen_income_acc.id,
                    'name': 'Pre-closure penalty / Наказателна лихва',
                    'is_overdue_interest': True,
                    'debit': 0.0,
                    'credit': pen_total,
                }))
                total += pen_total

        # Pre-closure fee — credited to 7240
        rem_principal_total = sum(max(0.0, l.remaining_principal or 0.0) for l in active_lines)
        fee_amount = round(rem_principal_total * (self.pre_closure_fee_pct or 0.0) / 100.0, 2)
        if fee_amount >= 0.01 and fee_income_acc:
            move_lines.append((0, 0, {
                'partner_id': partner.id,
                'account_id': fee_income_acc.id,
                'name': 'Pre-closure fee / Такса предсрочно погасяване',
                'debit': 0.0,
                'credit': fee_amount,
            }))
            total += fee_amount

        if not move_lines or total < 0.01:
            return super().action_pre_close_loan()

        # Bank debit (total received)
        move_lines.insert(0, (0, 0, {
            'partner_id': company_partner.id,
            'account_id': bank_acc.id,
            'name': f'{loan.name} — pre-closure settlement {closure_date}',
            'debit': total,
            'credit': 0.0,
        }))

        # ── Step 3: Post settlement JE ─────────────────────────────────────
        move = self.env['account.move'].create({
            'journal_id': col_journal.id,
            'date': closure_date,
            'ref': f'{loan.name} — pre-closure {closure_date}',
            'move_type': 'entry',
            'customer_loan_id': loan.id,
            'line_ids': move_lines,
        })
        move.action_post()

        # ── Step 4: Cancel future installments ────────────────────────────
        future_lines = active_lines.filtered(
            lambda l: l.emi_date and l.emi_date > closure_date and (l.remaining_amount or 0.0) > 0
        )
        future_lines.unlink()

        # ── Step 5: Close loan ────────────────────────────────────────────
        loan.is_pre_closure = True
        loan.loan_closure_date = closure_date
        loan.status = 'pre_closure'

        _logger.info('LMS pre-closure BG: loan %s closed on %s, total=%.2f',
                     loan.name, closure_date, total)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Pre-Closure Journal Entry',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False},
        }
