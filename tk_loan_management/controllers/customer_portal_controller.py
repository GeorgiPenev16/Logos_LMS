# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import base64
from odoo.addons.portal.controllers.portal import CustomerPortal, pager
from odoo import http, fields
from odoo.http import request


def get_message(types):
    """get message"""
    message = {
        'sent': {
            'type': 'info',
            'message': "The sanction letter has been sent for signing and acceptance."
        },
        'expired': {
            'type': 'warning',
            'message': "The sanction letter validity expired."
        },
        'rejected': {
            'type': 'danger',
            'message': "You rejected the sanction letter."
        },
        'cancelled': {
            'type': 'danger',
            'message': "You cancelled the loan."
        },
    }
    return message.get(types)


class CustomerPortalLoans(CustomerPortal):
    """Customer Portal Loans"""

    def _prepare_home_portal_values(self, counters):
        """Prepare home portal values"""
        rtn = super()._prepare_home_portal_values(counters)

        if "loan_count" in counters:
            rtn['loan_count'] = request.env[
                'customer.loan'].sudo().search_count(
                [('customer_id', '=', request.env.user.partner_id.id)])
        return rtn


class CustomerLoanPortal(http.Controller):
    """Customer Loan Portal"""

    # List view controller
    @http.route(
        ["/customer/my/loans", "/customer/my/loans/page/<int:page>"],
        type="http", website=True, auth="user")
    def customer_loan_list(self, page=1):
        """Customer loan list"""
        customer_loans_count = request.env[
            "customer.loan"].sudo().search_count(
            [('customer_id', '=', request.env.user.partner_id.id)])
        page_details = pager(url="/customer/my/loans",
                             total=customer_loans_count, page=page,
                             step=15)
        customer_loans = request.env["customer.loan"].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id)],
            limit=15,
            offset=page_details['offset'])
        vals = {
            "customer_loans": customer_loans,
            "page_name": 'customer_loans_portal_list_view',
            "pager": page_details
        }
        return request.render(
            "tk_loan_management.customer_loans_portal_list_template",
            vals)

    # requested document lines
    @http.route(
        ["/customer-documents-pending", "/customer-documents-pending/<int:page>"],
        type="http", website=True, auth="user")
    def customer_document_pending(self, page=1):
        """Customer loan list"""
        doc_req_count = len(request.env["customer.loan"].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id)]).mapped(
            'req_document_ids').filtered(lambda doc: doc.stage == 'pending'))

        page_details = pager(url="/customer-documents-pending",
                             total=doc_req_count, page=page,
                             step=15)

        customers_to_upload_documents = request.env["customer.loan"].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id),
             ('is_document_uploaded', '=', False)],
            limit=15,
            offset=page_details['offset'])

        customer_loans_ids = []

        for cstl_ids in customers_to_upload_documents:
            customer_loans_ids.append(cstl_ids.id)

        customer_loans = request.env["customer.loan"].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id),
             ('is_document_uploaded', '=', False)])

        for customer_loan in customer_loans:
            customer_loan._compute_customer_doc()
            break

        is_req_doc_pending = True
        for pending_doc_loan in customer_loans:
            if pending_doc_loan.req_document_ids:
                for pending_req_doc in pending_doc_loan.req_document_ids:
                    if pending_req_doc.stage not in ['submitted', 'rejected']:
                        is_req_doc_pending = False
                        break

        vals = {
            "customer_loans": customer_loans,
            'is_req_doc_pending': is_req_doc_pending,
            "page_name": 'customer_loans_portal_req_doc_list_view',
            "pager": page_details
        }
        return request.render(
            "tk_loan_management.customer_loans_portal_requested_document_list_template",
            vals)

    @http.route(
        ["/customer-collateral-pending", "/customer-collateral-pending/<int:page>"],
        type="http", website=True, auth="user")
    def customer_collateral_pending(self, page=1):
        """Customer collateral pending list"""
        col_doc_req_count = len(request.env["customer.loan"].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id),
             ('is_collateral_added', '=', False), ('is_collateral', '=', True)]).mapped(
            'req_collateral_ids').filtered(lambda collateral: collateral.stage == "pending").mapped(
            'cst_collateral_doc_lines_ids'))

        page_details = pager(url="/customer-collateral-pending",
                             total=col_doc_req_count, page=page,
                             step=15)

        customers_to_upload_collateral = request.env["customer.loan"].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id),
             ('is_collateral_added', '=', False), ('is_collateral', '=', True)],
            limit=15, offset=page_details['offset']).mapped('req_collateral_ids').filtered(
            lambda collateral: collateral.stage == "pending")

        customer_loans_ids = []

        for cstl_cl_ids in customers_to_upload_collateral:
            customer_loans_ids.append(cstl_cl_ids.id)

        customer_loans = request.env["customer.loan"].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id),
             ('is_collateral_added', '=', False)],
            limit=15,
            offset=page_details['offset'])

        request.env.user.partner_id.loan_to_review_for_collateral_upload = len(
            set(customer_loans_ids))

        request.env.user.partner_id.collateral_upload_pending = col_doc_req_count

        is_req_col_pending = True
        for pending_col_loan in customer_loans:
            if pending_col_loan.req_collateral_ids:
                for pending_req_col in pending_col_loan.req_collateral_ids:
                    if pending_req_col.stage not in ['submitted', 'rejected']:
                        is_req_col_pending = False
                        break

        for cs_loan in customer_loans:
            cs_loan._compute_customer_collateral()
            break

        vals = {
            "customer_loans": customer_loans,
            "is_req_col_pending": is_req_col_pending,
            "page_name": 'customer_loans_portal_req_collateral_list_view',
            "pager": page_details
        }
        return request.render(
            "tk_loan_management.customer_loans_portal_requested_collateral_list_template",
            vals)

    # customer req doc form view controller
    @http.route("/customer-req-doc-form/<string:access_token>",
                website=True, auth="user", type="http")
    def customer_doc_upload_details(self, access_token):
        """Customer doc upload details"""
        if not access_token:
            return request.redirect("/")

        req_document_line = request.env['customer.loan.request.document'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        loan_record = request.env['customer.loan'].sudo().search(
            [('id', '=', req_document_line.customer_loan_id.id)], limit=1)

        if not loan_record and not req_document_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        vals = {
            "req_document_line": req_document_line,
            "loan_record": loan_record,
            "page_name": 'portal_customer_loan_req_doc_form_view',
        }

        return request.render(
            "tk_loan_management.customer_loan_portal_requested_document_form_view", vals)

    # customer req doc form view controller
    @http.route("/customer-req-collateral-form/<string:access_token>",
                website=True, auth="user", type="http")
    def customer_collateral_upload_details(self, access_token):
        """Customer collateral upload details"""
        if not access_token:
            return request.redirect("/")

        req_collateral_line = request.env['customer.loan.request.collateral'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        loan_record = request.env['customer.loan'].sudo().search(
            [('id', '=', req_collateral_line.customer_loan_id.id)], limit=1)

        if not loan_record or not req_collateral_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        loan_record._compute_customer_collateral()

        vals = {
            "req_collateral_line": req_collateral_line,
            "loan_record": loan_record,
            "page_name": 'portal_customer_loan_req_collateral_form_view',
        }

        return request.render(
            "tk_loan_management.customer_loan_portal_requested_collateral_form_view", vals)

    @http.route(["/upload-req-col-line/<string:access_token>/<string:req_col_line_access_token>"],
                website=True, auth="user", type="http")
    def upload_req_col_line(self, access_token, req_col_line_access_token, **kwargs):
        """upload requested document"""
        if not access_token or not req_col_line_access_token:
            return request.redirect("/")

        loan_record_col_line = request.env['customer.collateral.lines'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        req_col_line = request.env['customer.loan.request.collateral'].sudo().search(
            [('access_token', '=', req_col_line_access_token)], limit=1)

        loan_record = request.env['customer.loan'].sudo().search(
            [('id', '=', loan_record_col_line.customer_loan_id.id)])

        if not loan_record or not loan_record_col_line or not req_col_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        for documents in loan_record_col_line:
            document_id = None

            if kwargs.get(documents.access_token):
                document_id = kwargs.get(documents.access_token)
                documents.document = base64.b64encode(
                    kwargs.get(documents.access_token).read()) if kwargs.get(
                    documents.access_token) else False
                documents.file_name = document_id.filename
            if kwargs.get(f"{documents.access_token}/description"):
                documents.customer_note = kwargs.get(f"{documents.access_token}/description")

        loan_record._compute_customer_collateral()

        return request.redirect(f'/customer-req-collateral-form/{req_col_line.access_token}')

    @http.route(["/delete-req-col-line/<string:access_token>/<string:req_col_line_access_token>"],
                website=True, auth="user", type="http")
    def delete_req_col_line(self, access_token, req_col_line_access_token):
        """upload requested document"""
        if not access_token or not req_col_line_access_token:
            return request.redirect("/")

        loan_record_col_line = request.env['customer.collateral.lines'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        req_col_line = request.env['customer.loan.request.collateral'].sudo().search(
            [('access_token', '=', req_col_line_access_token)], limit=1)

        loan_record = request.env['customer.loan'].sudo().search(
            [('id', '=', loan_record_col_line.customer_loan_id.id)])

        if not loan_record or not loan_record_col_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        for documents in loan_record_col_line:
            documents.document = False
            documents.customer_note = ''

        loan_record._compute_customer_doc()

        return request.redirect(f'/customer-req-collateral-form/{req_col_line.access_token}')

    # upload requested document
    @http.route(["/upload-req-doc/<string:access_token>/<string:req_doc_line_access_token>"],
                website=True, auth="user", type="http")
    def upload_req_doc(self, access_token, req_doc_line_access_token, **kwargs):
        """upload requested document"""
        if not access_token and not req_doc_line_access_token:
            return request.redirect("/")

        loan_record = request.env['customer.loan'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        req_doc_line = request.env['customer.loan.request.document'].sudo().search(
            [('access_token', '=', req_doc_line_access_token)], limit=1)

        if not loan_record or not req_doc_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        all_doc_uploaded = False

        for req_documents_line in req_doc_line.cst_doc_lines_ids:
            if req_documents_line.document:
                all_doc_uploaded = True
            else:
                all_doc_uploaded = False
                break

        if req_doc_line.stage == 'pending' and all_doc_uploaded:
            req_doc_line.stage = 'submitted'

        cst_loan_all_doc_uploaded = True
        for doc in loan_record.customer_loan_doc_ids:
            if not doc.document:
                cst_loan_all_doc_uploaded = False
                break
            cst_loan_all_doc_uploaded = True

        loan_record.is_document_uploaded = cst_loan_all_doc_uploaded

        loan_record._compute_customer_doc()

        vals = {
            'loan_record': loan_record,
            'req_document_line': req_doc_line,
            'page_name': 'portal_customer_loan_req_doc_form_view',
            'not_uploaded': all_doc_uploaded,
        }

        if not all_doc_uploaded:
            return request.render(
                "tk_loan_management.customer_loan_portal_requested_document_form_view", vals)

        activity_data = {
            'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
            'res_model_id': request.env['ir.model'].sudo().search(
                [('model', '=', 'customer.loan')]).id,
            'res_id': loan_record.id,
            'summary': f'{loan_record.customer_id.name} uploaded requested document of '
                       f'"{loan_record.approved_loan_type_id.name}" reference no. '
                       f'{req_doc_line.name} loan reference no {loan_record.name}',
            'date_deadline': fields.Datetime.now()
        }
        # Create the activity
        request.env['mail.activity'].sudo().create(activity_data)

        return request.redirect(f'/customer-req-doc-form/{req_doc_line.access_token}')

    @http.route(["/upload-req-doc-line/<string:access_token>/<string:req_doc_line_access_token>"],
                website=True, auth="user", type="http")
    def upload_req_doc_line(self, access_token, req_doc_line_access_token, **kwargs):
        """upload requested document"""
        if not access_token or not req_doc_line_access_token:
            return request.redirect("/")

        loan_record_doc_line = request.env['customer.loan.document.lines'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        req_doc_line = request.env['customer.loan.request.document'].sudo().search(
            [('access_token', '=', req_doc_line_access_token)], limit=1)

        loan_record = request.env['customer.loan'].sudo().search(
            [('id', '=', loan_record_doc_line.customer_loan_id.id)])

        if not loan_record or not loan_record_doc_line or not req_doc_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        for documents in loan_record_doc_line:
            document_id = None

            if kwargs.get(documents.access_token):
                document_id = kwargs.get(documents.access_token)
                documents.document = base64.b64encode(
                    kwargs.get(documents.access_token).read()) if kwargs.get(
                    documents.access_token) else False
                documents.file_name = document_id.filename

        loan_record._compute_customer_doc()

        return request.redirect(f'/customer-req-doc-form/{req_doc_line.access_token}')

    @http.route(["/delete-req-doc-line/<string:access_token>/<string:req_doc_line_access_token>"],
                website=True, auth="user", type="http")
    def delete_req_doc_line(self, access_token, req_doc_line_access_token):
        """upload requested document"""
        if not access_token or not req_doc_line_access_token:
            return request.redirect("/")

        loan_record_doc_line = request.env['customer.loan.document.lines'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        req_doc_line = request.env['customer.loan.request.document'].sudo().search(
            [('access_token', '=', req_doc_line_access_token)], limit=1)

        loan_record = request.env['customer.loan'].sudo().search(
            [('id', '=', loan_record_doc_line.customer_loan_id.id)])

        if not loan_record or not loan_record_doc_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        for documents in loan_record_doc_line:
            documents.document = False

        loan_record._compute_customer_doc()

        return request.redirect(f'/customer-req-doc-form/{req_doc_line.access_token}')

    @http.route(["/cancel-doc-request/<string:access_token>/<string:req_doc_line_access_token>"],
                website=True, auth="user", type="http")
    def cancel_doc_req(self, access_token, req_doc_line_access_token):
        """upload requested document"""
        if not access_token or not req_doc_line_access_token:
            return request.redirect("/")

        req_doc_line = request.env['customer.loan.request.document'].sudo().search(
            [('access_token', '=', req_doc_line_access_token)], limit=1)

        loan_record = request.env['customer.loan'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_record or not req_doc_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        if req_doc_line.stage == 'pending':
            req_doc_line.stage = 'rejected'
            for doc in req_doc_line.cst_doc_lines_ids:
                doc.document = False

        loan_record._compute_customer_doc()

        # loan_record.is_customer_cancelled_doc_req = True

        return request.redirect(f'/customer-req-doc-form/{req_doc_line.access_token}')

    @http.route(["/cancel-col-request/<string:access_token>/<string:req_col_line_access_token>"],
                website=True, auth="user", type="http")
    def cancel_col_req(self, access_token, req_col_line_access_token):
        """upload requested document"""
        if not access_token or not req_col_line_access_token:
            return request.redirect("/")

        req_col_line = request.env['customer.loan.request.collateral'].sudo().search(
            [('access_token', '=', req_col_line_access_token)], limit=1)

        loan_record = request.env['customer.loan'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_record or not req_col_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        if req_col_line.stage == 'pending':
            req_col_line.stage = 'rejected'

        for col in req_col_line.cst_collateral_doc_lines_ids:
            # col.status = 'rejected'
            col.sudo().unlink()

        loan_record._compute_customer_collateral()

        # loan_record.is_customer_cancelled_doc_req = True

        return request.redirect(f'/customer-req-collateral-form/{req_col_line.access_token}')

    # upload requested collateral
    @http.route([
        "/upload-req-collateral/<string:access_token>/<string:req_collateral_line_access_token>"],
        website=True, auth="user", type="http")
    def upload_req_collateral(self, access_token, req_collateral_line_access_token):
        """upload requested collateral"""
        if not access_token and not req_collateral_line_access_token:
            return request.redirect("/")

        loan_record = request.env['customer.loan'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        req_collateral_line = request.env['customer.loan.request.collateral'].sudo().search(
            [('access_token', '=', req_collateral_line_access_token)], limit=1)

        if not loan_record or not req_collateral_line:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        all_doc_uploaded = False

        for req_col_line in req_collateral_line.cst_collateral_doc_lines_ids:
            if req_col_line.document:
                all_doc_uploaded = True
            else:
                all_doc_uploaded = False
                break

        if req_collateral_line.stage == 'pending' and all_doc_uploaded:
            req_collateral_line.stage = 'submitted'

        for req_col in req_collateral_line.cst_collateral_doc_lines_ids:
            req_col.status = 'submitted'

        cst_loan_all_collateral_uploaded = True

        for req_col in loan_record.req_collateral_ids:
            if req_col.stage == 'pending':
                cst_loan_all_collateral_uploaded = False
                break
            cst_loan_all_collateral_uploaded = True

        loan_record.is_collateral_added = cst_loan_all_collateral_uploaded

        vals = {
            'loan_record': loan_record,
            'req_collateral_line': req_collateral_line,
            'page_name': 'portal_customer_loan_req_collateral_form_view',
            'not_uploaded': all_doc_uploaded,
        }

        if not all_doc_uploaded:
            return request.render(
                "tk_loan_management.customer_loan_portal_requested_collateral_form_view", vals)

        loan_record._compute_customer_collateral()

        activity_data = {
            'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
            'res_model_id': request.env['ir.model'].sudo().search(
                [('model', '=', 'customer.loan')]).id,
            'res_id': loan_record.id,
            'summary': f'{loan_record.customer_id.name} uploaded requested collateral document of'
                       f' "{loan_record.approved_loan_type_id.name}" loan reference '
                       f'no. {loan_record.name}.',
            'date_deadline': fields.Datetime.now()
        }
        # Create the activity
        request.env['mail.activity'].sudo().create(activity_data)

        return request.redirect(f'/customer-req-collateral-form/{req_collateral_line.access_token}')

    # Form view controller
    @http.route("/customer/my/loans-form/<string:access_token>",
                website=True, auth="user", type="http")
    def customer_loan_details(self, access_token):
        """Customer loan details"""
        if not access_token:
            return request.redirect("/")

        loan_record_obj = request.env['customer.loan']
        loan_record = request.env['customer.loan'].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_record:
            return request.redirect("/my")

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        prev_url = None
        next_url = None
        customer_loans = request.env['customer.loan'].sudo().search(
            [('customer_id', '=', request.env.user.partner_id.id)])
        customer_loans_ids = customer_loans.ids
        loan_index = customer_loans_ids.index(loan_record.id)
        if loan_index != 0 and customer_loans_ids[loan_index - 1]:
            prev_record = loan_record_obj.browse(customer_loans_ids[loan_index - 1])
            prev_url = f"/customer/my/loans-form/{prev_record.access_token}"
        if loan_index < len(customer_loans_ids) - 1 and \
                customer_loans_ids[loan_index + 1]:
            next_record = loan_record_obj.browse(customer_loans_ids[loan_index + 1])
            next_url = f"/customer/my/loans-form/{next_record.access_token}"

        vals = {
            "loan_record": loan_record,
            "page_name": 'portal_customer_loan_form_view',
            "prev_record": prev_url,
            "next_record": next_url,
        }

        if loan_record.cst_conf_stage != 'draft':
            vals['message'] = get_message(loan_record.cst_conf_stage)

        return request.render(
            "tk_loan_management.customer_loan_portal_form_view", vals)

    @http.route("/customer/download-closure-letter/<string:access_token>", auth='user', type='http',
                website=True)
    def download_closure_letter_pdf_report(self, access_token):
        """Download closure report pdf report"""

        if not access_token:
            return request.redirect('/')

        loan_record = request.env["customer.loan"].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_record:
            return request.redirect('/')

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        pdf_data = "tk_loan_management.customer_closure_letter_report_action"
        if loan_record.status == 'pre_closure':
            file_name = "Pre-Closure-letter.pdf"
        else:
            file_name = "Closure-letter.pdf"

        pdf_content = request.env['ir.actions.report'].sudo()._render_qweb_pdf(pdf_data,
                                                                               loan_record.id)
        response = request.make_response(pdf_content, headers=[('Content-Type', 'application/pdf')])
        response.headers.add('Content-Disposition', f'inline; filename="{file_name}"')
        return response

    @http.route("/customer/download-noc/<string:access_token>", auth='user', type='http',
                website=True)
    def download_noc_letter_pdf_report(self, access_token):
        """Download noc letter pdf report"""

        if not access_token:
            return request.redirect('/')

        loan_record = request.env["customer.loan"].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_record:
            return request.redirect('/')

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        pdf_data = "tk_loan_management.customer_noc_letter_report_action"
        file_name = "NOC.pdf"

        pdf_content = request.env['ir.actions.report'].sudo()._render_qweb_pdf(pdf_data,
                                                                               loan_record.id)
        response = request.make_response(pdf_content, headers=[('Content-Type', 'application/pdf')])
        response.headers.add('Content-Disposition', f'inline; filename="{file_name}"')
        return response

    @http.route("/customer/download-settlement-letter/<string:access_token>", auth='user',
                type='http',
                website=True)
    def download_settlement_letter_pdf_report(self, access_token):
        """Download settlement letter pdf report"""

        if not access_token:
            return request.redirect('/')

        loan_record = request.env["customer.loan"].sudo().search(
            [('access_token', '=', access_token)], limit=1)

        if not loan_record:
            return request.redirect('/')

        if (request.env.user.partner_id and loan_record and
                loan_record.customer_id.id != request.env.user.partner_id.id):
            return request.redirect('/my')

        pdf_data = "tk_loan_management.customer_settlement_letter_report_action"
        file_name = "Settlement-letter.pdf"

        pdf_content = request.env['ir.actions.report'].sudo()._render_qweb_pdf(pdf_data,
                                                                               loan_record.id)
        response = request.make_response(pdf_content, headers=[('Content-Type', 'application/pdf')])
        response.headers.add('Content-Disposition', f'inline; filename="{file_name}"')
        return response
