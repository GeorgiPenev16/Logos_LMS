# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import datetime

from markupsafe import Markup
from odoo import http
from odoo.http import request


def get_error_message(types, loan_no=None):
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
        },
        'link_expired': {
            'type': 'warning',
            'title': 'Sanction Letter Validity Expired!',
            'message': f"""Your sanction letter with application no. {loan_no} has expired. 
            Please click the button below to request the reopening of your sanction letter."""
        },
        'invalid_status': {
            'type': 'warning',
            'title': 'Sanction Letter Validity Expired!',
            'message': f"""Your sanction letter with application no. {loan_no} has expired."""
        },
        'loan_reject': {
            'type': 'danger',
            'title': 'Sanction Letter Rejected!',
            'message': f"""Your decision to reject the sanction letter with application no. 
                        {loan_no} has been noted. If you still wish to proceed with the loan,
                        please click the button below to request reopening the sanction letter."""
        },
        'loan_cancel': {
            'type': 'danger',
            'title': 'Loan Application Cancelled !',
            'message': f"""Your decision to cancel the loan with application no. {loan_no} has been 
                       noted."""
        },
        'request_submit': {
            'type': 'success',
            'title': 'Sanction Letter Reopen Request Submitted!',
            'message': f"""Your sanction letter reopening request with application no. {loan_no}
             has been submitted. You will be notified via email once the request is approved."""
        },
    }
    return error.get(types)


class SanctionLetterController(http.Controller):
    """Sanction Letter Controller"""

    # ------------------ portal controllers --------------------------------------------------------
    @http.route(
        ["/customer/loan-confirmation/", "/customer/loan-confirmation/<string:access_token>"],
        type="http", website=True, auth="user")
    def loan_confirmation_page(self, access_token=None):
        """loan confirmation page"""
        vals = {}
        loan_record = None
        sanction_letter = None
        if not access_token:
            vals['error'] = get_error_message('missing_access_token')
        else:
            sanction_letter = request.env['customer.loan.sanction.latter'].sudo().search([
                ('access_token', '=', access_token)
            ], limit=1)

            loan_record = sanction_letter.loan_id

            # loan_record = request.env["customer.loan"].sudo().search(
            #     [('access_token', '=', access_token)], limit=1)

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        if access_token and not sanction_letter:
            vals['error'] = get_error_message('invalid_access_token')
        if loan_record:
            if loan_record.status != 'confirmation':
                vals['error'] = get_error_message('invalid_status', loan_record.name)
            elif sanction_letter.cst_conf_stage in ['cancelled', 'rejected',
                                                    'expired'] and sanction_letter.cst_response_stage in [
                'reject_reopen', 'reopen_expired']:
                vals['error'] = get_error_message('request_submit', loan_record.name)
            elif sanction_letter.cst_conf_stage == 'cancelled':
                vals['error'] = get_error_message('loan_cancel', loan_record.name)
            elif sanction_letter.cst_conf_stage == 'rejected':
                vals['error'] = get_error_message('loan_reject', loan_record.name)
            elif sanction_letter.cst_conf_stage == 'expired':
                vals['error'] = get_error_message('link_expired', loan_record.name)
            vals["loan_record"] = loan_record
            vals["sanction_letter"] = sanction_letter
        return request.render(
            "tk_loan_management.loan_confirmation_template", vals)

    @http.route(["/customer/reject-loan/<string:access_token>"],
                type="http", website=True, auth="user")
    def reject_loan(self, access_token=None, **kwargs):
        """reject loan"""
        vals = {}
        loan_record = None
        sanction_letter = None

        if not access_token:
            vals['error'] = get_error_message('missing_access_token')
            return request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        sanction_letter = request.env['customer.loan.sanction.latter'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)

        if not sanction_letter:
            vals['error'] = get_error_message('invalid_access_token')
            return request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        loan_record = sanction_letter.loan_id
        if not loan_record:
            vals['error'] = get_error_message('invalid_access_token')
            return request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        sanction_letter.cst_conf_stage = 'rejected'
        sanction_letter.cst_loan_reject_reason = kwargs.get('cst_loan_reject_reason')

        body = Markup(
            '<strong style="color:red;">Sanction letter rejected by customer.</strong><br/>'
            f"<strong style='color:red;'>Reject Reason : "
            f"{kwargs.get('cst_loan_reject_reason')}</strong>")
        author = loan_record.company_id.partner_id.id
        partner = loan_record.responsible_id.id
        loan_record.message_post(body=body, message_type="email",
                                 author_id=author, partner_ids=[partner])
        return request.redirect(f"/customer/loan-confirmation/{access_token}")

    @http.route(["/customer/cancel-loan/<string:access_token>"],
                type="http", website=True, auth="user")
    def cancel_loan(self, access_token=None):
        """cancel loan"""
        vals = {}
        loan_record = None
        sanction_letter = None

        if not access_token:
            vals['error'] = get_error_message('missing_access_token')
            request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        sanction_letter = request.env['customer.loan.sanction.latter'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)

        if not sanction_letter:
            vals['error'] = get_error_message('invalid_access_token')
            request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        loan_record = sanction_letter.loan_id

        if not loan_record:
            vals['error'] = get_error_message('invalid_access_token')
            request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        body = Markup(
            '<strong style="color:red;">Loan request cancelled by customer.</strong><br/>')
        author = loan_record.company_id.partner_id.id
        partner = loan_record.responsible_id.id
        loan_record.message_post(body=body, message_type="email",
                                 author_id=author, partner_ids=[partner])

        sanction_letter.cst_conf_stage = 'cancelled'
        return request.redirect(f"/customer/loan-confirmation/{access_token}")

    @http.route(["/customer/loan-confirmation/reopen-request/<string:access_token>"],
                type="http", website=True, auth="user")
    def reopen_loan(self, access_token=None):
        """reopen loan"""
        vals = {}
        loan_record = None
        sanction_letter = None

        if not access_token:
            vals['error'] = get_error_message('missing_access_token')
            return request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        sanction_letter = request.env['customer.loan.sanction.latter'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)

        if not sanction_letter:
            if not loan_record:
                vals['error'] = get_error_message('invalid_access_token')
                return request.render(
                    "tk_loan_management.loan_confirmation_template", vals)

        loan_record = sanction_letter.loan_id

        if not loan_record:
            vals['error'] = get_error_message('invalid_access_token')
            return request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        if sanction_letter.cst_conf_stage == 'expired':
            sanction_letter.cst_response_stage = 'reopen_expired'
        elif sanction_letter.cst_conf_stage in ['rejected', 'cancelled']:
            sanction_letter.cst_response_stage = 'reject_reopen'
        return request.redirect(f"/customer/loan-confirmation/{access_token}")

    @http.route(["/customer/loan-confirmation/sign/<string:access_token>/accept"],
                type='json', auth="user", website=True)
    def customer_loan_application_accept(self, access_token=None, **kw):
        """Accept customer loan signature"""
        vals = {}
        loan_record = None
        sanction_letter = None

        if not access_token:
            vals['error'] = get_error_message('missing_access_token')
            return request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        sanction_letter = request.env['customer.loan.sanction.latter'].sudo().search([
            ('access_token', '=', access_token)
        ])

        if not sanction_letter:
            vals['error'] = get_error_message('invalid_access_token')
            return request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        loan_record = sanction_letter.loan_id

        # loan_record = request.env["customer.loan"].sudo().search(
        #     [('access_token', '=', access_token)], limit=1)
        if not loan_record:
            vals['error'] = get_error_message('invalid_access_token')
            return request.render(
                "tk_loan_management.loan_confirmation_template", vals)

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        sanction_letter.sign_loan_application(sign=kw.get('signature'), sign_by=kw.get('name'))
        sanction_letter.get_signature_hash()

        activity_data = {
            'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
            'res_model_id': request.env['ir.model'].sudo().search(
                [('model', '=', 'customer.loan')]).id,
            'res_id': loan_record.id,
            'summary': f'Sanction letter signed and accepted by {loan_record.customer_id.name}.',
            'date_deadline': datetime.datetime.now(),
        }
        if loan_record.responsible_id:
            activity_data['user_id'] = loan_record.responsible_id.id
        # Create the activity
        request.env['mail.activity'].sudo().create(activity_data)

        body = Markup(
            '<strong style="color:green;">Sanction letter signed and accepted by customer.'
            '</strong><br/>')
        author = loan_record.company_id.partner_id.id
        partner = loan_record.responsible_id.id
        loan_record.message_post(body=body, message_type="email",
                                 author_id=author, partner_ids=[partner])

        sanction_letter.cst_conf_stage = 'signed'
        loan_record.send_signature_certificate_email_to_customer()

        return {
            'force_refresh': True,
        }

    @http.route("/customer/download-loan-details/<string:access_token>", auth='user', type='http',
                website=True)
    def download_loan_details_pdf_report(self, access_token):
        """Download loan details pdf report"""

        if not access_token:
            return request.redirect('/')

        loan_record = request.env["customer.loan"].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_record:
            return request.redirect('/')

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        pdf_data = "tk_loan_management.customer_sanction_letter_action"
        file_name = "Sanction-Letter.pdf"

        pdf_content = request.env['ir.actions.report'].sudo()._render_qweb_pdf(pdf_data,
                                                                               loan_record.id)
        response = request.make_response(pdf_content, headers=[('Content-Type', 'application/pdf')])
        response.headers.add('Content-Disposition', f'inline; filename="{file_name}"')

        return response

    @http.route("/customer/download-signature-certificate/<string:access_token>", auth='user',
                type='http', website=True)
    def download_signature_certificate_pdf_report(self, access_token):
        """Download signature certificate pdf report"""
        if not access_token:
            return request.redirect('/')

        loan_record = request.env["customer.loan"].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_record:
            return request.redirect('/')

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        pdf_data = "tk_loan_management.customer_loan_signature_certificate_qweb_report_action"
        file_name = "Signature-Certificate.pdf"

        pdf_content = request.env['ir.actions.report'].sudo()._render_qweb_pdf(pdf_data,
                                                                               loan_record.id)
        response = request.make_response(pdf_content, headers=[('Content-Type', 'application/pdf')])
        response.headers.add('Content-Disposition', f'inline; filename="{file_name}"')
        return response
