# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class RequestDocumentFromCustomerWizard(models.TransientModel):
    """request document from customer wizard"""
    _name = 'request.document.from.customer'
    _description = __doc__

    @api.model
    def default_get(self, fields):
        """Default get"""
        record = super().default_get(fields)
        customer_loan = self.env['customer.loan'].browse(self.env.context.get('active_id'))
        record['customer_loan_id'] = customer_loan.id
        doc_list = []
        for documents in customer_loan:
            if documents.customer_loan_doc_ids:
                for doc in documents.customer_loan_doc_ids:
                    if doc.document or doc.is_requested_from_customer:
                        doc_list.append(doc.document_type_id.id)

        record['uploaded_document_ids'] = [(6, 0, doc_list)]
        return record

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")
    uploaded_document_ids = (
        fields.Many2many(comodel_name="customer.document.type", relation="uploaded_document_rel",
                         column1="uploaded_doc_id", column2="customer_loan_id"))

    req_document_from_customer_ids = (
        fields.Many2many(
            comodel_name="customer.document.type", relation="request_document_rel",
            column1="requested_doc_id", column2="customer_loan_id",
        ))

    def action_request_document(self):
        """action request document"""
        for rec in self:
            documents = rec.customer_loan_id.mapped('customer_loan_doc_ids').mapped(
                'document_type_id').mapped('id')

            for doc in rec.req_document_from_customer_ids:
                if doc.id in documents:
                    req_doc = self.env['customer.loan.document.lines'].search(
                        [('customer_loan_id', '=', rec.customer_loan_id.id),
                         ('document_type_id', '=', doc.id)])
                    requested_doc = rec.customer_loan_id.req_document_ids.filtered(
                        lambda status: status.stage == 'pending').mapped(
                        'cst_doc_lines_ids').mapped('document_type_id').mapped('id')
                    if req_doc.document:
                        raise ValidationError(
                            _(f"The {req_doc.document_type_id.name} has been uploaded.\n"
                              f"You cannot request a document that has already been uploaded.\n"
                              f"Please remove the {req_doc.document_type_id.name} document before "
                              f"making a request."))

                    if not req_doc.document and req_doc.status == 'rejected':
                        raise ValidationError(_(
                            f"Document status of {req_doc.document_type_id.name} is rejected!"
                            f"\nPlease change {req_doc.document_type_id.name} status to "
                            f"draft before requesting."))

                    if doc.id in requested_doc:
                        raise ValidationError(
                            _(f"The {doc.name} has already been requested and is pending upload."))
                    req_doc.is_requested_from_customer = True
                else:
                    rec.customer_loan_id.customer_loan_doc_ids = [
                        (0, 0, {'document_type_id': doc.id,
                                'is_requested_from_customer': True
                                })
                    ]

            requested_docs = []
            requested_docs_ids = rec.customer_loan_id.req_document_ids.filtered(
                lambda line: line.stage == 'pending').mapped('cst_doc_lines_ids').ids

            for req_doc in rec.customer_loan_id.customer_loan_doc_ids:
                if (req_doc.is_requested_from_customer and not req_doc.document
                        and req_doc.id not in requested_docs_ids
                        and req_doc.document_type_id.id in rec.req_document_from_customer_ids.ids):
                    requested_docs.append(req_doc.id)

            rec.customer_loan_id.req_document_ids = [(0, 0, {
                'cst_doc_lines_ids': [(6, 0, requested_docs)],
                'stage': 'pending',
            })]

            rec.customer_loan_id.is_document_uploaded = False

            mail_template = self.env.ref('tk_loan_management.document_request_mail_template')
            if not rec.customer_loan_id.email:
                raise ValidationError(
                    _("Please add the customer's email address before requesting the documents."))
            if mail_template:
                mail_template.send_mail(
                    rec.customer_loan_id.id, force_send=True,
                    email_values={'author_id': rec.customer_loan_id.company_id.partner_id.id})
