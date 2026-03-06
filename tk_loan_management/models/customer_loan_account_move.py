# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api

class CustomerLoanAccountMove(models.Model):
    """Customer Loan Account Move"""
    _inherit = "account.move"
    _description = __doc__

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")
    customer_installment_id = fields.Many2one(comodel_name="account.move")
    entry_post_date = fields.Date()
    is_disbursement = fields.Boolean()
    loan_line_id = fields.Many2one(comodel_name='customer.loan.lines')
    is_initial_fee_journal = fields.Boolean()

    def action_post(self):
        """action post"""
        # inherit of the function from account.move to validate a new tax and the price unit of a
        # down payment
        res = super().action_post()

        for rec in self:
            if rec.customer_loan_id and rec.move_type == 'entry' and rec.is_disbursement:
                rec.entry_post_date = fields.Date.today()
                mail_template = self.env.ref(
                    'tk_loan_management.loan_disbursement_confirmation_mail_template')
                if mail_template:
                    mail_template.send_mail(
                        rec.customer_loan_id.id, force_send=True,
                        email_values={'author_id': rec.customer_loan_id.company_id.partner_id.id})
        return res


class CustomerLoanAccountMoveLines(models.Model):
    """Customer Loan Account Move"""
    _inherit = "account.move.line"
    _description = __doc__

    is_cst_penalty_on_penalty = fields.Boolean(default=False)
    is_cst_principle_penalty = fields.Boolean(default=False)
    is_cst_principle = fields.Boolean(default=False)
    fee_amount = fields.Monetary(string="Fee")
    loan_price = fields.Monetary(string="Price")
    is_overdue_interest = fields.Boolean(default=False)
    is_interest = fields.Boolean(default=False)
    is_principal = fields.Boolean(default=False)
    is_fee = fields.Boolean(default=False)


    # loan line

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create method to take loan_price same as price unit
        """
        res = super(CustomerLoanAccountMoveLines, self).create(vals_list)
        for rec in res:
            rec.loan_price = rec.price_unit - rec.fee_amount
        return res

    @api.onchange('loan_price')
    def _onchange_loan_price(self):
        """
        Method to reflect the unit price when user change the loan price
        """
        for rec in self:
            rec.price_unit = rec.loan_price + rec.fee_amount

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        """Update loan price when there is a change into price unit"""
        for rec in self:
            rec.loan_price = rec.price_unit - rec.fee_amount
