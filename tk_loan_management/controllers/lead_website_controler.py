# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import secrets
import base64
from markupsafe import Markup
from odoo import http, fields
from odoo.http import request
from odoo.tools.mail import is_html_empty


def get_error_message(types):
    """get error message"""
    error = {
        'missing_access_token': {
            'type': 'warning',
            'title': 'Invalid URL!',
            'message': """Sorry, but this url is invalid. If you continue to encounter issues, 
            reach out to support for assistance."""
        },
        'invalid_access_token': {
            'type': 'danger',
            'title': 'Invalid URL!',
            'message': """The URL you are accessing is invalid. Please re-open link from the 
            email. If you continue to encounter issues, reach out to support for assistance."""
        }
    }
    return error.get(types)


class leadWebsiteController(http.Controller):
    """lead website controller"""

    @http.route('/customer-loan-request', type='http', auth='public', website=True)
    def get_customer_loan_request(self):
        """Get salon package quote request"""
        loan_types = request.env['customer.loan.type'].sudo().search([])
        values = {
            'loan_types': loan_types,
        }
        return request.render('tk_loan_management.customer_loan_request_form', values)

    @http.route('/get-loan-type-details', website=True, auth='public', type='jsonrpc')
    def get_document_details(self, **kw):
        """Get document details"""
        show_loan_type_details = request.env['customer.loan.type'].sudo().search(
            [('id', '=', int(kw.get('loan_type')))])

        documents = [{'name': doc.document_type_id.name}
                     for doc in show_loan_type_details.loan_doc_ids]

        tc = show_loan_type_details.terms_and_conditions if not is_html_empty(
            show_loan_type_details.terms_and_conditions) else False
        rpt = show_loan_type_details.repayment_terms if not is_html_empty(
            show_loan_type_details.repayment_terms) else False

        return {'documents': documents, 'tc': tc, 'rpt': rpt}

    # Create lead and redirect to thank you page
    @http.route('/create-loan-request', type='http', auth='public', website=True)
    def create_loan_lead(self, **kw):
        """Create salon lead"""
        data = {
            'type': 'lead',
            'contact_name': kw.get('full_name'),
            'email_from': kw.get('email_address'),
            'phone': kw.get('customer_phone'),
            'approved_loan_type_id': int(kw.get('loan_type')),
            'requested_loan_amount': kw.get('loan_amount'),
        }
        if kw.get('installment_type'):
            data['requested_installment_type'] = kw.get('installment_type')
        if kw.get('term'):
            data['requested_term'] = kw.get('term')
        if kw.get('customer_mobile'):
            data['mobile'] = kw.get('customer_mobile')
        if kw.get('purpose'):
            data['description'] = kw.get('purpose')

        utm = request.env['utm.medium'].sudo().search([('name', '=', 'Website')], limit=1)
        if utm:
            data['medium_id'] = utm.id

        data['access_token'] = secrets.token_urlsafe(16)

        salesperson_id = request.env['ir.config_parameter'].sudo().get_param(
            'tk_loan_management.sales_person_id')

        data['user_id'] = int(salesperson_id) if salesperson_id else False
        data['loan_req_status'] = 'in_progress'

        approved_loan_type_id = request.env['customer.loan.type'].sudo().search(
            [('id', '=', int(kw.get('loan_type')))])

        data['name'] = f"{kw.get('full_name')} has requested a {approved_loan_type_id.name}"

        lead = request.env['crm.lead'].sudo().create(data)

        for rec in lead:
            rec.crm_customer_doc_ids = [
                (0, 0, {'document_type_id': doc.document_type_id.id,
                        'document': base64.b64encode(
                            kw.get(doc.document_type_id.name).read()) if kw.get(
                            doc.document_type_id.name) else False,
                        'file_name': kw.get(doc.document_type_id.name).filename if kw.get(
                            doc.document_type_id.name) else False,
                        }) for doc in
                approved_loan_type_id.loan_doc_ids]
            rec.terms_and_conditions = approved_loan_type_id.terms_and_conditions
            rec.terms_and_conditions_template_id = (
                approved_loan_type_id.terms_and_conditions_template_id.id
                if approved_loan_type_id.terms_and_conditions_template_id
                else False
            )
            rec.repayment_terms = approved_loan_type_id.repayment_terms
            rec.repayment_terms_template_id = (
                approved_loan_type_id.repayment_terms_template_id.id
                if approved_loan_type_id.repayment_terms_template_id
                else False
            )
            base_url = request.httprequest.url_root
            url = f"{base_url}track-loan/{rec.access_token}"
            rec.customer_requested_loan_tracking_url = url

        company = request.env.company
        company_id = lead.company_id.partner_id.id if lead.company_id else company.partner_id.id

        mail_template = request.env.ref('tk_loan_management.loan_request_submitted_mail_template')

        if mail_template:
            mail_template.with_context({
                'lead_company': company,
                'date_time': fields.Datetime.now()
            }).sudo().send_mail(lead.id, force_send=True,
                                email_values={'author_id': company_id})

        # Create the activity
        if lead.user_id:
            activity_data = {
                'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
                'res_model_id': request.env['ir.model'].sudo().search(
                    [('model', '=', 'crm.lead')]).id,
                'res_id': lead.id,
                'user_id': lead.user_id.id,
                'summary': 'Follow up on the new lead',
                'date_deadline': fields.Datetime.now()
            }
            request.env['mail.activity'].sudo().create(activity_data)

        return request.redirect(f'/loan-request-submitted/{lead.access_token}')

    @http.route(['/track-loan/', '/track-loan/<string:access_token>'],
                type='http', auth='public', website=True)
    def track_loan(self, access_token=None):
        """track loan"""
        vals = {}
        loan_req_lead = None
        if not access_token:
            vals['error'] = get_error_message('missing_access_token')
        else:
            loan_req_lead = request.env["crm.lead"].sudo().search(
                [('access_token', '=', access_token), ('active', 'in', [True, False])], limit=1)

        if access_token and not loan_req_lead:
            vals['error'] = get_error_message('invalid_access_token')

        vals['loan_req_lead'] = loan_req_lead

        return request.render('tk_loan_management.track_loan_request', vals)

    # Thank you page template
    @http.route(
        ['/loan-request-submitted/', '/loan-request-submitted/<string:access_token>'],
        type='http', auth='public', website=True)
    def redirect_to_thank_you(self, access_token=None):
        """Redirect to thank you"""
        vals = {}
        loan_req_lead = None
        if not access_token:
            vals['error'] = get_error_message('missing_access_token')
        else:
            loan_req_lead = request.env["crm.lead"].sudo().search(
                [('access_token', '=', access_token)], limit=1)

        if access_token and not loan_req_lead:
            vals['error'] = get_error_message('invalid_access_token')

        vals['loan_req_lead'] = loan_req_lead

        return request.render('tk_loan_management.loan_request_created', vals)

    @http.route(["/customer-cancel-requested-loan/<string:access_token>"],
                type="http", website=True, auth="public")
    def cancel_loan(self, access_token=None):
        """cancel loan"""
        vals = {}
        loan_req_lead = None
        if not access_token:
            vals['error'] = get_error_message('missing_access_token')
            request.render(
                "tk_loan_management.track_loan_request", vals)

        loan_req_lead = request.env["crm.lead"].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_req_lead:
            vals['error'] = get_error_message('invalid_access_token')
            request.render(
                "tk_loan_management.track_loan_request", vals)

        author_id = (
            loan_req_lead.company_id.partner_id.id
            if loan_req_lead.company_id
            else request.env.company.partner_id.id
        )

        body = Markup(
            '<strong style="color:red;">Loan request cancelled by customer.</strong><br/>'
        )
        author = author_id
        partner = loan_req_lead.user_id.id if loan_req_lead.user_id else request.env.user.id
        loan_req_lead.message_post(body=body, message_type="email",
                                   author_id=author, partner_ids=[partner])

        loan_req_lead.loan_req_status = 'cancelled'
        return request.redirect(f"/track-loan/{access_token}")
