# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup
from odoo import models, fields, api


class CustomerDocumentRejectReasonWizard(models.TransientModel):
    """Customer Document Reject Reason Wizard"""
    _name = "customer.document.reject.reason.wizard"
    _description = __doc__

    @api.model
    def default_get(self, fields):
        """Default get"""
        record = super().default_get(fields)
        customer_loan_doc = self.env['customer.loan.document.lines'].browse(
            self.env.context.get('active_id'))
        record['customer_loan_doc_id'] = customer_loan_doc.id
        return record

    customer_loan_doc_id = fields.Many2one(comodel_name="customer.loan.document.lines")
    reason = fields.Text()

    def action_reject_reason(self):
        """action reject reason"""
        self.customer_loan_doc_id.status = 'rejected'
        self.customer_loan_doc_id.reason = self.reason
        self.customer_loan_doc_id.validator_id = self.env.user.id

        body = Markup(
            f'<strong>Document : </strong>{self.customer_loan_doc_id.document_type_id.name}<br/>'
            f'<strong>Rejected By : </strong>{self.env.user.name}<br/>'
            f'<strong>Reason : </strong>{self.reason}<br/>')

        self.customer_loan_doc_id.customer_loan_id.message_post(
            body=body, message_type="email",
            partner_ids=[
                self.customer_loan_doc_id.customer_loan_id.responsible_id.partner_id.id]
            if self.customer_loan_doc_id.customer_loan_id.responsible_id.partner_id.id
            else None,
            author_id=self.customer_loan_doc_id.customer_loan_id.responsible_id.partner_id.id)
