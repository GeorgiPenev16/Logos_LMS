# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class RequestCollateralFromCustomerWizard(models.TransientModel):
    """request collateral from customer wizard"""
    _name = 'request.collateral.from.customer'
    _description = __doc__

    @api.model
    def default_get(self, fields):
        """Default get"""
        record = super().default_get(fields)
        customer_loan = self.env['customer.loan'].browse(self.env.context.get('active_id'))
        record['customer_loan_id'] = customer_loan.id

        collateral_list = []
        for documents in customer_loan:
            if documents.collateral_ids:
                for doc in documents.collateral_ids:
                    if doc.document or doc.is_requested_from_customer:
                        collateral_list.append(doc.collateral_type_id.id)

        record['uploaded_collateral_ids'] = [(6, 0, collateral_list)]
        return record

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")

    uploaded_collateral_ids = (
        fields.Many2many(comodel_name="customer.collateral.type",
                         relation="uploaded_collateral_rel",
                         column1="uploaded_doc_id", column2="customer_loan_id"))

    req_collateral_from_customer_ids = (
        fields.Many2many(comodel_name="customer.collateral.type",
                         relation="requested_collateral_rel", column1="requested_doc_id",
                         column2="customer_loan_id"))

    def action_request_collateral(self):
        """action request collateral"""
        for rec in self:
            collateral = rec.customer_loan_id.mapped('collateral_ids').mapped(
                'collateral_type_id').mapped('id')

            if rec.customer_loan_id.req_collateral_ids:
                for req_col_line in rec.customer_loan_id.req_collateral_ids:
                    if req_col_line.stage == 'pending':
                        raise ValidationError(
                            _("Please upload the pending collateral before making a request."))

            for doc in rec.req_collateral_from_customer_ids:
                if doc.id in collateral:
                    req_collateral = self.env['customer.collateral.lines'].search(
                        [('customer_loan_id', '=', rec.customer_loan_id.id),
                         ('collateral_type_id', '=', doc.id)], limit=1)
                    if req_collateral.is_requested_from_customer:
                        rec.customer_loan_id.collateral_ids = [
                            (0, 0, {'collateral_type_id': doc.id,
                                    'is_requested_from_customer': True,
                                    'status': 'requested'
                                    })
                        ]
                    req_collateral.is_requested_from_customer = True
                else:
                    rec.customer_loan_id.collateral_ids = [
                        (0, 0, {'collateral_type_id': doc.id,
                                'is_requested_from_customer': True,
                                'status': 'requested'
                                })
                    ]

            requested_collaterals = []
            collateral_type_ids = []
            for req_doc in rec.customer_loan_id.collateral_ids:
                if (req_doc.is_requested_from_customer and not req_doc.document
                        and req_doc.id not in requested_collaterals
                        and req_doc.status == 'requested'
                        and req_doc.collateral_type_id.id in
                        rec.req_collateral_from_customer_ids.ids):
                    requested_collaterals.append(req_doc.id)
                    collateral_type_ids.append(req_doc.collateral_type_id.id)

            rec.customer_loan_id.req_collateral_ids = [(0, 0, {
                'cst_collateral_doc_lines_ids': [(6, 0, requested_collaterals)],
                'req_collateral_ids': [(6, 0, collateral_type_ids)]
            })]

            rec.customer_loan_id.is_collateral_added = False

            mail_template = self.env.ref('tk_loan_management.collateral_request_mail_template')
            if not rec.customer_loan_id.email:
                raise ValidationError(_(
                    "Please add the customer's email address before requesting the collateral"
                    " documents."))
            if mail_template:
                mail_template.send_mail(
                    rec.customer_loan_id.id, force_send=True,
                    email_values={'author_id': rec.customer_loan_id.company_id.partner_id.id})
