# -*- coding: utf-8 -*-
"""
GROUP B — Disbursement Overhaul

Overrides action_disburse_loan() to produce the correct Bulgarian NAS
journal entry:

    DR  4110  Вземания по кредити — текуща вноска  (ST: next 12-month principal)
    DR  262   Предоставени дългосрочни заеми        (LT: remainder)
        CR  5031  Bank — Collections                (full loan amount)

The base module produces a single-account debit (DR receivable_account_id).
We let super() run (for validations + mail), then replace the draft JE lines.

If lms_fee_invoice_on_disburse is True, a validated customer invoice is also
created on the Loan Fee Invoice journal (LINV) for the processing fee → 7220.
"""
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CustomerLoanDisburseBG(models.Model):
    _inherit = 'customer.loan'

    def _compute_st_lt_split(self):
        """Return (st_amount, lt_amount) based on 12-month installment window.

        ST = sum of installment_amount for lines due within 12 months
             from disbursement_date (or today if not set).
        LT = loan_amount - st_amount.

        Both values are clamped to [0, loan_amount].
        """
        self.ensure_one()
        ref_date = self.disbursement_date or fields.Date.today()
        cutoff = ref_date + relativedelta(months=12)
        st_amount = sum(
            line.installment_amount
            for line in self.loan_lines_ids
            if line.emi_date and line.emi_date <= cutoff and not line.display_type
        )
        st_amount = min(max(st_amount, 0.0), self.loan_amount)
        lt_amount = max(self.loan_amount - st_amount, 0.0)
        return st_amount, lt_amount

    def action_disburse_loan(self):
        """Override: replace single-account JE with Bulgarian 4110+262 split."""
        self.ensure_one()
        company = self.env.company

        lt_acc = company.lms_lt_loan_account_id
        st_acc = company.lms_st_loan_account_id
        disb_journal = company.lms_disbursement_journal_id
        ops_journal = company.lms_operations_journal_id
        fee_income_acc = company.lms_fee_income_account_id
        inv_journal = company.lms_invoice_journal_id

        # ── Fallback: if BG accounts not configured, use base behaviour ─────
        if not (lt_acc and st_acc and disb_journal):
            return super().action_disburse_loan()

        # ── Compute split ────────────────────────────────────────────────────
        st_amount, lt_amount = self._compute_st_lt_split()

        bank_acc = disb_journal.default_account_id
        if not bank_acc:
            raise UserError(_(
                'Disbursement journal %s has no default account configured.'
            ) % disb_journal.name)

        # ── Call super() — runs validations, sends mail, updates status ──────
        # super() also creates a draft journal_entry_id which we will replace.
        result = super().action_disburse_loan()
        if result:
            # super() returned an error display_message — propagate it
            return result

        # ── Replace the base draft JE with our BG split ──────────────────────
        move = self.journal_entry_id
        if move and move.state == 'draft':
            line_vals = []

            # ST debit line (4110)
            if st_amount > 0:
                line_vals.append((0, 0, {
                    'partner_id': self.customer_id.id,
                    'account_id': st_acc.id,
                    'name': _('%(loan)s — Current portion ST (4110)') % {'loan': self.name},
                    'debit': st_amount,
                    'credit': 0.0,
                }))

            # LT debit line (262)
            if lt_amount > 0:
                line_vals.append((0, 0, {
                    'partner_id': self.customer_id.id,
                    'account_id': lt_acc.id,
                    'name': _('%(loan)s — Long-term portion LT (262)') % {'loan': self.name},
                    'debit': lt_amount,
                    'credit': 0.0,
                }))

            # Bank credit line (5031)
            line_vals.append((0, 0, {
                'partner_id': self.env.company.partner_id.id,
                'account_id': bank_acc.id,
                'name': _('%(loan)s — Disbursement') % {'loan': self.name},
                'debit': 0.0,
                'credit': self.loan_amount,
            }))

            move.write({
                'journal_id': disb_journal.id,
                'ref': self.name,
                'line_ids': [(5, 0, 0)] + line_vals,  # (5) deletes all existing lines
            })
            move.action_post()

        # ── Fee invoice (optional) ────────────────────────────────────────────
        if (company.lms_fee_invoice_on_disburse
                and self.is_processing_fee
                and self.processing_fee_amount > 0
                and self.processing_fee_deduct_from == 'disbursement'
                and fee_income_acc
                and inv_journal):
            self._create_fee_invoice_bg(
                fee_amount=self.processing_fee_amount,
                fee_account=fee_income_acc,
                journal=inv_journal,
            )

        return result

    def _create_fee_invoice_bg(self, fee_amount, fee_account, journal):
        """Create and validate a customer invoice for the origination fee (7220)."""
        self.ensure_one()
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'journal_id': journal.id,
            'invoice_date': self.disbursement_date or fields.Date.today(),
            'ref': _('%(loan)s — Origination fee') % {'loan': self.name},
            'customer_loan_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': _('Loan origination fee — %(loan)s') % {'loan': self.name},
                'account_id': fee_account.id,
                'quantity': 1.0,
                'price_unit': fee_amount,
            })],
        })
        invoice.action_post()
        return invoice
