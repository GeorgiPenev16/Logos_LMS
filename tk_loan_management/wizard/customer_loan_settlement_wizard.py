# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from ..models.customer_loan import display_message


class CustomerLoanSettlementWizard(models.TransientModel):
    """Customer Loan Settlement Wizard"""
    _name = "customer.loan.settlement.wizard"
    _description = __doc__

    @api.model
    def default_get(self, fields):
        """Default get"""
        record = super().default_get(fields)
        loan_id = self.env['customer.loan'].browse(self.env.context.get('active_id'))
        record['loan_id'] = loan_id.id
        return record

    loan_id = fields.Many2one(comodel_name="customer.loan")
    currency_id = fields.Many2one(related="loan_id.currency_id")
    remaining_loan_principle_amount = fields.Monetary(
        related="loan_id.remaining_loan_principle_amount",
        currency_field="currency_id")
    outstanding_penalty = fields.Monetary(related="loan_id.outstanding_penalty",
                                          currency_field="currency_id")
    settlement_amount = fields.Monetary(currency_field="currency_id")

    def action_settlement(self):
        """action settlement"""
        if self.settlement_amount <= 0:
            raise ValidationError(_("Settlement amount must be greater than zero."))

        loan = self.loan_id
        if not loan:
            return display_message(_("Active Loan missing"),
                                   _("To settle the loan, there must be an active loan, but none was found."))

        if not loan.repayment_journal_item_id:
            return display_message(
                _("Repayment Journal Missing"),
                _("To create journal entry, select repayment journal item in loan journal details."))
        if not loan.bank_cash_account:
            return display_message(
                _("Bank Account Missing"),
                _("To create journal entry, select bank account in loan account details."))
        if not loan.receivable_account_id:
            return display_message(
                _("Account Receivable Missing"),
                _("To create journal entry, select account receivable in loan account details."))

        journal_lines = [(0, 0, {
            'partner_id': loan.env.company.partner_id.id,
            'account_id': loan.bank_cash_account.id,
            'debit': self.settlement_amount
        }), (0, 0, {
            'partner_id': loan.customer_id.id,
            'account_id': loan.receivable_account_id.id,
            'credit': self.settlement_amount
        })]

        journal_entry_id = self.env['account.move'].create({
            'journal_id': loan.repayment_journal_item_id.id,
            'ref': loan.name,
            'move_type': 'entry',
            'customer_loan_id': loan.id,
            'line_ids': journal_lines
        })

        loan.settlement_date = fields.Date.today()
        loan.settlement_journal_entry_id = journal_entry_id.id
        loan.settlement_amount = self.settlement_amount
        forgiven_debt = (self.outstanding_penalty +
                         loan.remaining_amount - self.settlement_amount)
        loan.forgiven_debt = forgiven_debt if forgiven_debt >= 0 else 0
        loan.status = "settlement"
        loan.loan_closure_date = fields.Date.today()

        for loan_line in loan.loan_lines_ids:
            if loan_line.journal_entry_id and loan_line.journal_entry_id.state != 'posted':
                loan_line.journal_entry_id.state = 'cancel'

        for penalty in self.loan_id.penalty_lines_ids:
            if penalty.journal_entry_id and penalty.journal_entry_id.state != 'posted':
                penalty.journal_entry_id.state = 'cancel'

        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entry',
            'res_model': 'account.move',
            'res_id': journal_entry_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False},
        }
