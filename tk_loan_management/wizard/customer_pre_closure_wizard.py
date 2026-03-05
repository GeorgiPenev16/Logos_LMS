# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

from ..models.customer_loan import display_message


class CustomerPreClosureWizard(models.TransientModel):
    """Customer Pre Closure Wizard"""
    _name = "customer.pre.closure.wizard"
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
    is_pre_closure_charge = fields.Boolean(default=False)
    pre_closure_charge = fields.Monetary(currency_field="currency_id", string="Charge")
    pre_closure_interest = fields.Float(string="Interest")
    pre_closure_interest_amount = fields.Monetary(currency_field="currency_id",
                                                  string="Interest Amount",
                                                  compute="_compute_pre_close_payments")
    pre_closure_installment_amount = fields.Monetary(currency_field="currency_id",
                                                     string="Installment Amount",
                                                     compute="_compute_pre_close_payments")
    pre_closure_total_installment_amount = fields.Monetary(currency_field="currency_id",
                                                           string="Total Installment Amount",
                                                           compute="_compute_pre_close_payments")

    @api.constrains('pre_closure_charge', 'is_pre_closure_charge')
    def _check_pre_closure_charge(self):
        """check pre closure charge"""
        if self.is_pre_closure_charge and self.pre_closure_charge <= 0:
            raise ValidationError(_("The Pre-Closure charge must be greater than zero."))

    @api.constrains('pre_closure_interest')
    def _check_pre_closure_interest(self):
        """check pre closure interest"""
        if self.pre_closure_interest < 0:
            raise ValidationError(_("Pre-closure interest amount must be greater than zero."))

    @api.onchange('is_pre_closure_charge')
    def _onchange_is_pre_closure_charge(self):
        """onchange pre closure charge"""
        self._compute_pre_close_payments()

    @api.depends('pre_closure_charge', 'pre_closure_interest', 'remaining_loan_principle_amount')
    def _compute_pre_close_payments(self):
        """compute pre close payments"""
        interest_amount = 0
        if self.pre_closure_interest > 0:
            interest_amount = (
                    (self.remaining_loan_principle_amount * self.pre_closure_interest) / 100)
        closure_charge = self.pre_closure_charge if self.is_pre_closure_charge else 0
        self.pre_closure_interest_amount = interest_amount
        self.pre_closure_installment_amount = self.remaining_loan_principle_amount
        self.pre_closure_total_installment_amount = (
                interest_amount + self.pre_closure_installment_amount + closure_charge)

    def action_pre_close_loan(self):
        """action pre-close loan"""
        if self.outstanding_penalty > 0:
            raise ValidationError(
                _("Please pay the outstanding penalty amount before pre-closing loan."))

        # if len(self.loan_id.mapped('loan_lines_ids').mapped('journal_entry_id').filtered(
        #         lambda amt_res: amt_res.state != 'posted')) > 0:
        #     raise ValidationError(
        #         _("Please pay the outstanding installment before pre-closing loan."))

        outstanding_installments = self.loan_id.loan_lines_ids.filtered(
            lambda line: line.remaining_amount > 0 and line.emi_date <= fields.Date.today())

        if outstanding_installments:
            raise ValidationError(_("Please pay the outstanding installment before Pre-Closure."))

        if self.pre_closure_total_installment_amount <= 0:
            raise ValidationError(_("Pre-Closure installment amount must be greater than zero."))

        if not self.loan_id.repayment_journal_item_id:
            return display_message(
                _("Repayment Journal Missing"),
                _("To create journal entry, select repayment journal item in loan journal details."))
        if not self.loan_id.bank_cash_account:
            return display_message(
                _("Bank Account Missing"),
                _("To create journal entry, select bank account in loan account details."))
        if not self.loan_id.receivable_account_id:
            return display_message(
                _("Account Receivable Missing"),
                _("To create journal entry, select account receivable in loan account details."))
        if not self.loan_id.interest_income_account_id:
            return display_message(
                _("Interest Income Account Missing"),
                _("To create journal entry, select interest income account in loan account details."))

        installment_line = []
        installment_line.append((0, 0, {
            'display_type': 'line_section',
            'name': f"""The last {len(self.loan_id.mapped('loan_lines_ids').filtered(
                lambda installment: installment.status != 'paid'))} remaining installments have been canceled due to loan pre-closure.""",
        }))
        installment_line.append((0, 0, {
            'display_type': 'line_section',
            'name': "Pre-Closure Installment",
        }))

        self.loan_id.loan_lines_ids = installment_line
        pre_closure_inst = self.env['customer.loan.lines'].create({
            'installments_no': 'Pre-closure installment',
            'emi_date': fields.Date.today(),
            'installment_amount': self.pre_closure_installment_amount,
            'interest_amount': self.pre_closure_interest_amount,
            'total_installment_amount': self.pre_closure_total_installment_amount,
            'remaining_amount': 0,
            'principal_balance': 0,
            'customer_loan_id': self.loan_id.id
        })

        journal_lines = [(0, 0, {
            'partner_id': self.env.company.partner_id.id,
            'account_id': self.loan_id.bank_cash_account.id,
            'name': 'Pre Closure Installment',
            'is_principal': True,
            'debit': self.pre_closure_installment_amount
        }), (0, 0, {
            'partner_id': self.loan_id.customer_id.id,
            'account_id': self.loan_id.receivable_account_id.id,
            'is_principal': True,
            'name': 'Pre Closure Installment',
            'credit': self.pre_closure_installment_amount
        })]

        if self.pre_closure_interest > 0:
            journal_lines += [(0, 0, {
                'partner_id': self.env.company.partner_id.id,
                'account_id': self.loan_id.bank_cash_account.id,
                'name': 'Pre Closure Interest',
                'is_interest': True,
                'debit': self.pre_closure_interest_amount,
            }), (0, 0, {
                'partner_id': self.loan_id.customer_id.id,
                'account_id': self.loan_id.interest_income_account_id.id,
                'name': 'Pre Closure Interest',
                'is_interest': True,
                'credit': self.pre_closure_interest_amount,
            })]

        if self.is_pre_closure_charge:
            journal_lines += [(0, 0, {
                'partner_id': self.env.company.partner_id.id,
                'account_id': self.loan_id.bank_cash_account.id,
                'name': 'Pre Closure Charges',
                'debit': self.pre_closure_charge,
            }), (0, 0, {
                'partner_id': self.loan_id.customer_id.id,
                'account_id': self.loan_id.interest_income_account_id.id,
                'name': 'Pre Closure Charges',
                'credit': self.pre_closure_charge,
            })]

        journal_entry_id = self.env['account.move'].create({
            'journal_id': self.loan_id.repayment_journal_item_id.id,
            'ref': self.loan_id.name,
            'move_type': 'entry',
            'loan_line_id': pre_closure_inst.id,
            'customer_loan_id': self.loan_id.id,
            'line_ids': journal_lines
        })

        self.loan_id.is_pre_closure = True
        self.loan_id.loan_closure_date = fields.Date.today()
        self.loan_id.status = 'pre_closure'

        inst_included_in_pre_close = self.loan_id.loan_lines_ids.filtered(
            lambda
                line: line.display_type != "line_section" and line.status == 'unpaid' and line.emi_date > fields.Date.today())
        inst_included_in_pre_close.unlink()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entry',
            'res_model': 'account.move',
            'res_id': journal_entry_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False},
        }
