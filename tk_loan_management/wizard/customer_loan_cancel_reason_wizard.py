# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup
from odoo import models, fields, api


class CustomerLoanCancelReasonWizard(models.TransientModel):
    """Customer Loan Reject Reason Wizard"""
    _name = "customer.loan.cancel.reason.wizard"
    _description = __doc__

    @api.model
    def default_get(self, fields):
        """Default get"""
        record = super().default_get(fields)
        customer_loan = self.env['customer.loan'].browse(self.env.context.get('active_id'))
        record['customer_loan_id'] = customer_loan.id
        return record

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")
    reason = fields.Text()

    def action_cancel_reason(self):
        """action cancel reason"""
        if self.customer_loan_id.status in ['draft', 'confirm','dept_approval', 'confirmation']:
            self.customer_loan_id.cancel_reason = self.reason

            body = Markup(f'<strong>Loan Request : </strong>{self.customer_loan_id.name}<br/>'
                          f'<strong>Cancelled By : </strong>{self.env.user.name}<br/>'
                          f'<strong>Reason : </strong>{self.reason}<br/>')

            self.customer_loan_id.message_post(
                body=body,
                message_type="email",
                partner_ids=[
                    self.customer_loan_id.responsible_id.partner_id.id
                    if self.customer_loan_id.responsible_id.partner_id.id
                    else None
                ],
                author_id=self.customer_loan_id.responsible_id.partner_id.id
            )


            self.customer_loan_id.status = 'cancel'
