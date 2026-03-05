# -*- coding: utf-8 -*-
# Copyright 2024 - Today Techkhedut.
# Part of Techkhedut. See LICENSE file for full copyright and licensing detail
import base64
import datetime
import json
import logging
import secrets
from calendar import monthrange
from datetime import timedelta
from hashlib import sha256

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.mail import is_html_empty

_logger = logging.getLogger(__name__)

_UNITS_NEUTER = {1: "едно", 2: "две"}
_UNITS_FEMININE = {1: "една", 2: "две"}
_UNITS_MASCULINE = {1: "един", 2: "два"}

_UNITS_COMMON = {
    0: "нула", 1: "едно", 2: "две", 3: "три", 4: "четири", 5: "пет", 6: "шест",
    7: "седем", 8: "осем", 9: "девет", 10: "десет",
    11: "единадесет", 12: "дванадесет"
}
_HUNDREDS = {1: "сто", 2: "двеста", 3: "триста"}


def display_message(title, message):
    """Display message"""
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': title,
            'type': 'warning',
            'message': message,
            'sticky': False,
        }
    }


def post_message(self, body, partners, author, location):
    """post message"""
    for rec in self:
        if location == 'loan':
            rec.message_post(body=body, message_type="email",
                             partner_ids=partners,
                             author_id=author)
        elif location == 'doc':
            rec.customer_loan_id.message_post(body=body, message_type="email")


class CustomerLoan(models.Model):
    """Customer Loan"""
    _name = 'customer.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = __doc__

    name = fields.Char()

    lead_id = fields.Many2one(comodel_name="crm.lead")

    # Customer Details
    customer_id = fields.Many2one(comodel_name="res.partner", required=True)
    user_id = fields.Many2one(comodel_name="res.users")
    customer_tooltip = fields.Char(default="Customer must be an user.")
    phone = fields.Char(related="customer_id.phone", store=True)
    email = fields.Char(compute="_compute_email",
                        string="User Email", store=True)
    app_date = fields.Date(string="Application Date",
                           default=fields.Date.today(), required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True,
                                 readonly=False,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='company_id.currency_id', string='Currency')

    # Requested loan details
    approved_loan_type_id = fields.Many2one(
        comodel_name="customer.loan.type", ondelete='restrict')
    requested_loan_amount = fields.Monetary(currency_field="currency_id")
    requested_start_date = fields.Date(
        default=fields.Date.today(), required=True)
    requested_installment_type = fields.Selection(
        selection=[('monthly', 'Monthly'), ('quarterly',
                                            'Quarterly'), ('yearly', 'Yearly')],
        default="monthly")
    requested_term = fields.Integer()

    # Approved Loan details
    approval_date = fields.Date()
    loan_amount = fields.Monetary(currency_field="currency_id", tracking=True)
    start_date = fields.Date(default=fields.Date.today(),
                             tracking=True, required=True)
    term = fields.Integer(tracking=True)
    installment_type = fields.Selection(
        selection=[('monthly', 'Monthly'), ('quarterly',
                                            'Quarterly'), ('yearly', 'Yearly')],
        default="monthly")
    installment_amount = fields.Monetary(currency_field="currency_id")
    is_collateral = fields.Boolean()
    is_penalty = fields.Boolean(default=False)
    is_fee = fields.Boolean()
    fee_amount = fields.Float()
    is_initial_fee = fields.Boolean()
    is_initial_fee_paid = fields.Boolean(compute='_compute_is_initial_fee_paid')
    initial_fee_amount = fields.Float()
    is_grace_period = fields.Boolean()
    grace_period = fields.Integer()  # In Month
    # Other Details
    responsible_id = fields.Many2one(
        comodel_name='res.users', default=lambda self: self.env.user, string='Responsible',
        required=True, tracking=True)

    # Purpose
    loan_purpose = fields.Text(string="Purpose")

    # Bank details
    # Customer bank details
    cst_bank_name = fields.Char(string="Bank Name", required=True)
    cst_bank_account_number = fields.Char(
        string="Account Number", required=True)
    cst_bank_branch_name = fields.Char(string="Branch Name")
    cst_bank_branch_code = fields.Char(string="Branch Code", required=True)
    cst_bank_swift_bic_code = fields.Char(
        string="SWIFT/BIC Code", required=True)

    # Documents
    customer_loan_doc_ids = fields.One2many(
        comodel_name="customer.loan.document.lines", inverse_name="customer_loan_id")
    is_document_uploaded = fields.Boolean(default=True)

    compute_customer_doc = fields.Boolean(compute="_compute_customer_doc")

    req_document_ids = (
        fields.One2many(comodel_name="customer.loan.request.document",
                        inverse_name="customer_loan_id"))

    # Collateral
    collateral_ids = fields.One2many(comodel_name="customer.collateral.lines",
                                     inverse_name="customer_loan_id")
    is_collateral_added = fields.Boolean(default=True)

    compute_customer_collateral = fields.Boolean(
        compute="_compute_customer_collateral")

    req_collateral_ids = (
        fields.One2many(comodel_name="customer.loan.request.collateral",
                        inverse_name="customer_loan_id"))

    # Loan evaluation
    interest_rate = fields.Float()

    interest_amount = fields.Monetary(currency_field="currency_id", compute='_compute_loan_details')
    remaining_amount = fields.Monetary(currency_field="currency_id",
                                       compute="_compute_loan_details")
    total_amount = fields.Monetary(
        currency_field="currency_id", compute="_compute_total_amount")
    remaining_loan_principle_amount = (
        fields.Monetary(currency_field="currency_id",
                        compute="_compute_loan_details",
                        string="Remaining Principle Amount"))

    loan_lines_ids = fields.One2many(comodel_name="customer.loan.lines",
                                     inverse_name="customer_loan_id")

    # Sanction letter
    cst_conf_stage = fields.Selection([
        ('draft', 'Draft'), ('sent', 'Sent'), ('signed', 'Signed'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], compute='_compute_sanction_latter_stages')

    cst_response_stage = fields.Selection([
        ('draft', 'Draft'), ('reject_reopen', 'Reject Reopen'),
        ('reopen_expired', 'Reopen Expired')
    ], default='draft', compute='_compute_sanction_latter_stages')

    sent_date_time = fields.Datetime()
    accept_date_time = fields.Datetime()
    expiry_date = fields.Date(compute="_compute_expiry_date", store=True)
    is_expired = fields.Boolean(default=False)
    cst_sign = fields.Image()
    sign_by = fields.Char()
    signature_hash = fields.Char()
    event_hash = fields.Char()
    cst_loan_reject_reason = fields.Text()

    # Sanction latter
    sanction_latter_ids = fields.One2many('customer.loan.sanction.latter', 'loan_id')

    # Disbursement
    disbursement_payment_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer')
    ])
    is_processing_fee = fields.Boolean(default=False)
    processing_fee_deduct_from = fields.Selection(
        selection=[('disbursement', 'Disbursement'), ('customer', 'Customer')],
        string="Deduct From",
        default="disbursement", required=True)
    processing_fee_type = fields.Selection(
        selection=[('fixed', 'Fixed'), ('percentage', 'Percentage')],
        default='fixed')
    processing_fee_percentage = fields.Float(
        default=1, string="Fee Percentage")
    processing_fee_amount = fields.Monetary(
        currency_field="currency_id", string="Processing Fee")
    processing_fee_tax_ids = fields.Many2many(
        comodel_name="account.tax", string="Taxes ")
    installment_start_date = fields.Date(
        default=fields.Date.today(), required=True)
    disbursement_date = fields.Date(default=fields.Date.today())
    current_installment_amount = fields.Monetary(currency_field="currency_id")
    current_installment_due_date = fields.Date()
    end_date = fields.Date(compute="_compute_end_date", store=True)
    # vendor bill for loan disbursement
    bill_id = fields.Many2one(comodel_name="account.move")
    bill_state = fields.Selection(
        related="bill_id.payment_state", string="Bill State")
    # invoice for process fee from customer
    invoice_id = fields.Many2one(comodel_name="account.move")
    invoice_state = fields.Selection(
        related="invoice_id.state", string="Invoice State")

    # Penalty
    penalty_type = fields.Selection(selection=[('fixed', 'Fixed'), ('percentage', 'Percentage')],
                                    default='fixed')
    penalty_percentage = fields.Float(string="Percentage")
    penalty_amount = fields.Monetary(
        currency_field="currency_id", string="Penalty")
    outstanding_penalty = fields.Monetary(currency_field="currency_id",
                                          compute="_compute_outstanding_penalty")
    penalty_tax_ids = fields.Many2one(
        comodel_name="account.tax", string="Taxes")
    penalty_lines_ids = fields.One2many(comodel_name="customer.loan.installment.penalty.lines",
                                        inverse_name="customer_loan_id")
    penalty_tooltip = fields.Char(
        default="Compound interest will not be applied to fixed-type.")

    loan_od_count = fields.Integer()

    # settlement
    settlement_date = fields.Date()
    settlement_invoice_id = fields.Many2one(comodel_name="account.move")
    settlement_invoice_state = fields.Selection(related="settlement_invoice_id.state",
                                                string="Settlement Payment Status")
    settlement_amount = fields.Monetary(currency_field="currency_id")
    forgiven_debt = fields.Monetary(currency_field="currency_id")
    show_settlement = fields.Boolean(compute="_compute_show_settlement")
    settlement_journal_entry_id = fields.Many2one('account.move')

    # Terms and conditions
    terms_and_conditions_template_id = fields.Many2one(
        comodel_name="customer.terms.and.conditions.template")
    terms_and_conditions = fields.Html()
    # Repayment terms
    repayment_terms_template_id = fields.Many2one(
        comodel_name="customer.repayment.terms.template")
    repayment_terms = fields.Html()
    # Reject
    reject_reason = fields.Text(tracking=True)
    # Cancel
    cancel_reason = fields.Text(tracking=True)

    status = fields.Selection(
        selection=[('draft', 'Draft'), ('confirm', 'Confirm'),
                   ('dept_approval', 'Department Approval'),
                   ('confirmation', 'Confirmation'),
                   ('disbursement', 'Disbursement'),
                   ('in_progress', 'In Progress'), ('closure', 'Closure'),
                   ('pre_closure', 'Pre Closure'),
                   ('settlement', 'Settlement'), ('rejected', 'Rejected'), ('cancel', 'Cancelled')],
        default="draft", group_expand="_group_expand_status", tracking=True)

    # Back-end field
    customer_loan_portal_url = fields.Char(
        compute="_compute_customer_loan_portal_url")
    customer_requested_document_portal_url = fields.Char(
        compute="_compute_customer_requested_document_portal_url")
    access_token = fields.Char()
    loan_closure_date = fields.Date()
    total_penalty = fields.Monetary(
        currency_field="currency_id", compute="_compute_total_penalty")
    is_pre_closure = fields.Boolean()
    is_settlement = fields.Boolean()
    send_revised_sanction_letter = fields.Boolean()

    # Overdue penalty interest
    is_overdue_penalty_interest = fields.Boolean(string='Apply overdue interest')
    od_penalty_interest = fields.Float(string="Overdue Interest")

    # Account information
    receivable_account_id = fields.Many2one('account.account',
                                            string="Account Receivable",
                                            domain=[('account_type', '=', 'asset_receivable')])
    bank_cash_account = fields.Many2one('account.account',
                                        string="Bank Account",
                                        domain=[('account_type', '=', 'asset_cash')])

    interest_income_account_id = fields.Many2one('account.account',
                                                 string="Interest Income Account",
                                                 domain=[
                                                     ('account_type', '=', 'income')])

    journal_item_id = fields.Many2one('account.journal', 'Disbursement Journal')
    repayment_journal_item_id = fields.Many2one('account.journal', 'Repayment Journal')

    journal_entry_id = fields.Many2one('account.move')

    remain_installment_count = fields.Integer(compute='_compute_remain_instalment_count',
                                              store=True)
    credit_balance = fields.Monetary()
    send_recalculate_inst_mail = fields.Boolean()

    def _group_expand_status(self, stages, domain):
        """set kanban group in sequence"""
        return ['draft', 'confirm', 'dept_approval', 'confirmation', 'disbursement', 'in_progress',
                'closure', 'pre_closure', 'settlement', 'rejected', 'cancel']

    # compute methods
    @api.depends('customer_loan_doc_ids', 'customer_loan_doc_ids.document')
    def _compute_customer_doc(self):
        """compute customer doc uploaded"""
        for rec in self:
            customers_all_document_uploaded = True
            loans_all_document_uploaded = True

            # for set boolean in res partner
            customers_to_upload_documents = self.search(
                [('customer_id', '=', rec.customer_id.id)]).mapped(
                'req_document_ids').filtered(
                lambda document: document.stage == 'pending')

            pending_docs = customers_to_upload_documents.mapped(
                'cst_doc_lines_ids')

            customer_loans_ids = []

            for cstl_ids in customers_to_upload_documents:
                customer_loans_ids.append(cstl_ids.customer_loan_id.id)

            # for set boolean in customer loan
            for doc in rec.req_document_ids:
                if doc.stage in ['pending']:
                    loans_all_document_uploaded = False
                    break
                loans_all_document_uploaded = True

            # for set boolean in res.partner
            if customers_to_upload_documents:
                customers_all_document_uploaded = False
            else:
                customers_all_document_uploaded = True

            rec.compute_customer_doc = loans_all_document_uploaded
            rec.is_document_uploaded = loans_all_document_uploaded

            rec.customer_id.loan_to_review_for_doc_upload = len(
                set(customer_loans_ids))
            rec.customer_id.docs_upload_pending = len(pending_docs)
            rec.customer_id.is_document_uploaded = customers_all_document_uploaded

    @api.depends('compute_customer_collateral', 'collateral_ids', 'req_collateral_ids')
    def _compute_customer_collateral(self):
        """compute is collateral added"""
        for rec in self:
            loan_all_collateral_added = True

            # for set boolean in res partner
            pending_loan = self.search(
                [('customer_id', '=', rec.customer_id.id), ('is_collateral', '=', True)]).mapped(
                'req_collateral_ids').filtered(
                lambda collateral: collateral.stage == "pending")

            customers_to_upload_collateral = pending_loan.mapped(
                'cst_collateral_doc_lines_ids')

            customer_loans_ids = []

            for cst_cl_ids in pending_loan:
                customer_loans_ids.append(cst_cl_ids.customer_loan_id.id)

            for req_col in rec.req_collateral_ids:
                if req_col.stage == 'pending':
                    loan_all_collateral_added = False
                    break
                loan_all_collateral_added = True

            pending_loan_collateral_added = False if pending_loan else True

            rec.is_collateral_added = loan_all_collateral_added
            rec.compute_customer_collateral = loan_all_collateral_added

            rec.customer_id.loan_to_review_for_collateral_upload = len(
                set(customer_loans_ids))
            rec.customer_id.collateral_upload_pending = len(
                customers_to_upload_collateral)
            rec.customer_id.is_collateral_added = pending_loan_collateral_added

    @api.depends('customer_id', 'customer_id.email', 'user_id.login')
    def _compute_email(self):
        """compute email"""
        for rec in self:
            email = ""
            user = self.env['res.users'].search(
                [('partner_id', '=', rec.customer_id.id)])
            if user:
                email = user.login
            else:
                email = rec.customer_id.email
            rec.email = email

    @api.depends('penalty_lines_ids', 'penalty_lines_ids.penalty_amount')
    def _compute_total_penalty(self):
        """compute total penalty"""
        for rec in self:
            penalty_amount = 0
            if rec.penalty_lines_ids:
                for penalty in rec.penalty_lines_ids:
                    penalty_amount += penalty.penalty_amount
            rec.total_penalty = penalty_amount

    @api.depends('loan_lines_ids')
    def _compute_total_amount(self):
        """compute total amount"""
        total_amount = 0
        for rec in self:
            if rec.loan_lines_ids:
                for loan in rec.loan_lines_ids:
                    total_amount += loan.total_installment_amount
            rec.total_amount = total_amount

    @api.depends('loan_lines_ids', 'loan_lines_ids.journal_entry_ids',
                 'loan_lines_ids.journal_entry_ids.state')
    def _compute_loan_details(self):
        """compute remaining amount"""
        for rec in self:
            remaining_loan_principle_amount = rec.loan_amount
            remaining_amount = rec.total_amount
            # total_amount = 0
            interest_amount = 0

            loan_lines_ids = rec.loan_lines_ids
            if not loan_lines_ids:
                rec.remaining_amount = remaining_amount
                rec.remaining_loan_principle_amount = remaining_loan_principle_amount
                # rec.total_amount = total_amount
                rec.interest_amount = interest_amount
                continue
            for installment in loan_lines_ids:
                journal_entry_ids = installment.journal_entry_ids
                if journal_entry_ids:
                    paid_amount = sum(journal_entry_ids.filtered(
                        lambda line: line.state == "posted").mapped('amount_total'))

                    remaining_amount = round(remaining_amount - paid_amount, 2)

                    paid_principal_amount = sum(journal_entry_ids.filtered(
                        lambda e: e.state == 'posted').mapped('line_ids').filtered(
                        lambda l: l.is_principal and l.credit > 0).mapped('credit'))
                    remaining_loan_principle_amount -= paid_principal_amount

                # total_amount += installment.total_installment_amount
                interest_amount += installment.interest_amount

            rec.remaining_amount = remaining_amount
            rec.remaining_loan_principle_amount = remaining_loan_principle_amount
            # rec.total_amount = total_amount
            rec.interest_amount = interest_amount

    @api.depends('loan_lines_ids', 'loan_lines_ids.status')
    def _compute_remain_instalment_count(self):
        """
        Method to compute remaining installment count
        """
        for rec in self:
            installments = rec.loan_lines_ids
            remain_installments = 0

            remain_grace_period_installments_cnt = len(installments.filtered(
                lambda line: line.is_grace_installment and line.status != 'paid'))

            remain_installments_count = len(installments.filtered(
                lambda line: not line.is_grace_installment and line.status != 'paid'))

            if remain_installments_count == 1 and remain_grace_period_installments_cnt <= 0:
                rec.remain_installment_count = remain_installments
                continue

            remain_installments += (
                    remain_grace_period_installments_cnt + remain_installments_count)
            rec.remain_installment_count = remain_installments

    @api.depends('penalty_lines_ids', 'penalty_lines_ids.journal_entry_id',
                 'penalty_lines_ids.journal_entry_id.state')
    def _compute_outstanding_penalty(self):
        """compute outstanding penalty"""
        for rec in self:
            outstanding_penalty = 0
            if rec.penalty_lines_ids:
                for penalty in rec.penalty_lines_ids:
                    if penalty.journal_entry_id.state != 'posted':
                        outstanding_penalty += penalty.penalty_amount
            rec.outstanding_penalty = outstanding_penalty

    @api.depends('loan_lines_ids', 'loan_lines_ids.journal_entry_ids')
    def _compute_is_initial_fee_paid(self):
        """
        Method to compute is initial fee paid
        """
        for rec in self:
            initial_fee_paid = False
            installments = rec.loan_lines_ids
            if installments:
                initial_fee_journal = installments.mapped('journal_entry_ids').filtered(
                    lambda line: line.is_initial_fee_journal)
                if initial_fee_journal:
                    initial_fee_paid = True
            rec.is_initial_fee_paid = initial_fee_paid

    @api.depends('end_date')
    def _compute_show_settlement(self):
        """compute show settlement for settlement button"""
        for rec in self:
            today = fields.Date.today()
            if rec.status == 'in_progress' and today > rec.end_date and (
                    rec.remaining_amount > 0 or rec.outstanding_penalty > 0):
                rec.show_settlement = False
            else:
                rec.show_settlement = True

    @api.depends('sent_date_time')
    def _compute_expiry_date(self):
        """compute expiry date"""
        for rec in self:
            expiry_date = False
            if rec.sent_date_time:
                sanction_letter_expire_days = self.env['ir.config_parameter'].sudo().get_param(
                    'tk_loan_management.sanction_letter_expire_days')
                if not sanction_letter_expire_days:
                    expiry_date = rec.sent_date_time + timedelta(days=3)
                else:
                    expiry_date = rec.sent_date_time + timedelta(
                        days=int(sanction_letter_expire_days))
            rec.expiry_date = expiry_date

    @api.depends('term')
    def _compute_end_date(self):
        """compute end date"""
        for rec in self:
            end_date = None
            if rec.installment_start_date:
                if rec.installment_type == 'monthly':
                    end_date = rec.installment_start_date + \
                               relativedelta(months=rec.term - 1)
                elif rec.installment_type == 'quarterly':
                    end_date = rec.installment_start_date + \
                               relativedelta(months=(rec.term - 1) * 3)
                elif rec.installment_type == 'yearly':
                    end_date = rec.installment_start_date + relativedelta(
                        months=(rec.term - 1) * 12)
            rec.end_date = end_date

    @api.depends('sanction_latter_ids', 'sanction_latter_ids.access_token')
    def _compute_customer_loan_portal_url(self):
        """compute customer loan portal url"""
        for rec in self:
            url = ""
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip(
                '/')
            if rec.sanction_latter_ids:
                active_sanction_latter = rec.sanction_latter_ids[-1]
                url = f"{base_url}customer/loan-confirmation/{active_sanction_latter.access_token}"
            rec.customer_loan_portal_url = url

    @api.depends('req_document_ids')
    def _compute_customer_requested_document_portal_url(self):
        """compute customer requested document portal url"""
        for rec in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip(
                '/')
            url = f"{base_url}/my"
            rec.customer_requested_document_portal_url = url

    @api.depends('sanction_latter_ids', 'sanction_latter_ids.cst_conf_stage',
                 'sanction_latter_ids.cst_response_stage')
    def _compute_sanction_latter_stages(self):
        """
        Compute is sanction latter sign.
        """
        for rec in self:
            cst_conf_stage = None
            cst_response_stage = None

            if rec.sanction_latter_ids:
                sanction_latter = rec.sanction_latter_ids[-1]
                cst_conf_stage = sanction_latter.cst_conf_stage
                cst_response_stage = sanction_latter.cst_response_stage
            rec.cst_conf_stage = cst_conf_stage
            rec.cst_response_stage = cst_response_stage

    @api.onchange('terms_and_conditions_template_id')
    def _onchange_terms_and_conditions_template_id(self):
        """onchange terms and conditions template id"""
        for rec in self:
            rec.terms_and_conditions = rec.terms_and_conditions_template_id.terms_and_conditions

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """
        onchange customer id retrieve it's account number
        """
        for rec in self:
            customer_id = rec.customer_id
            if customer_id:
                rec.cst_bank_account_number = customer_id.bank_account

    @api.onchange('repayment_terms_template_id')
    def _onchange_repayment_terms(self):
        """onchange repayment terms"""
        for rec in self:
            rec.repayment_terms = rec.repayment_terms_template_id.repayment_terms

    @api.onchange('requested_term')
    def _onchange_requested_term(self):
        """onchange requested term"""
        for rec in self:
            rec.term = rec.requested_term

    @api.onchange('requested_installment_type')
    def _onchange_requested_installment_type(self):
        """onchange requested installment type"""
        for rec in self:
            rec.requested_term = 0
            rec.installment_type = rec.requested_installment_type

    @api.onchange('installment_type')
    def _onchange_installment_type(self):
        """onchange installment type"""
        for rec in self:
            rec.term = 0

    @api.onchange('processing_fee_type')
    def _onchange_processing_fee_type(self):
        """onchange processing fee type"""
        for rec in self:
            if rec.processing_fee_type == 'fixed':
                rec.processing_fee_amount = 0
            elif rec.processing_fee_type == 'percentage':
                self._onchange_processing_fee_percentage()

    @api.onchange('processing_fee_percentage')
    def _onchange_processing_fee_percentage(self):
        """onchange processing fee percentage"""
        for rec in self:
            if rec.processing_fee_percentage > 0:
                rec.processing_fee_amount = (
                                                    rec.loan_amount * rec.processing_fee_percentage) / 100
            else:
                rec.processing_fee_amount = 0

    @api.onchange('requested_start_date')
    def _onchange_requested_start_date(self):
        """Onchange requested start date"""
        for rec in self:
            rec.start_date = rec.requested_start_date

    @api.onchange('start_date')
    def _onchange_start_date(self):
        """Onchange start date"""
        for rec in self:
            rec.installment_start_date = rec.start_date

    @api.onchange('approved_loan_type_id')
    def _onchange_approved_loan_type_id(self):
        """Onchange loan type id"""
        for rec in self:
            rec.customer_loan_doc_ids = [(5, 0, 0)]
            approved_loan_type_id = rec.approved_loan_type_id

            if approved_loan_type_id:
                rec.customer_loan_doc_ids = [(0, 0, {'document_type_id': doc.document_type_id.id,
                                                     }) for doc in
                                             approved_loan_type_id.loan_doc_ids]
                rec.terms_and_conditions = approved_loan_type_id.terms_and_conditions
                rec.terms_and_conditions_template_id = (
                    approved_loan_type_id.terms_and_conditions_template_id.id)
                rec.repayment_terms = approved_loan_type_id.repayment_terms
                rec.repayment_terms_template_id = (
                    approved_loan_type_id.repayment_terms_template_id.id)
                rec.is_fee = approved_loan_type_id.is_fee
                rec.fee_amount = approved_loan_type_id.fee_amount
                rec.is_initial_fee = approved_loan_type_id.is_initial_fee
                rec.initial_fee_amount = approved_loan_type_id.initial_fee_amount
                rec.is_overdue_penalty_interest = approved_loan_type_id.is_overdue_penalty_interest
                rec.od_penalty_interest = approved_loan_type_id.od_penalty_interest

    @api.onchange('is_initial_fee')
    def _onchange_initial_fee(self):
        """
        Method to remove initial fee amount if is_initial_fee is not True
        """
        for rec in self:
            if not rec.is_initial_fee:
                rec.initial_fee_amount = 0.0

    @api.onchange('is_fee')
    def _onchange_is_fee(self):
        """
        Method to remove fee if is_fee is not true
        """
        for rec in self:
            if not rec.is_fee:
                rec.fee_amount = 0.0

    @api.onchange('is_grace_period')
    def _onchange_is_grace_period(self):
        """
        Method to remove grace period when is_grace_period's value is false
        """
        for rec in self:
            rec.grace_period = 0.0

    @api.ondelete(at_uninstall=False)
    def _prevent_deletion_of_loan(self):
        """ Prevent loan deletion state is not draft """
        for rec in self:
            if rec.status != 'draft':
                raise ValidationError(
                    _("You can only delete loans that are in the Draft status."))

    @api.constrains('processing_fee_percentage')
    def _check_processing_fee_percentage(self):
        """check processing fee percentage"""
        for rec in self:
            if rec.processing_fee_percentage <= 0:
                raise ValidationError(
                    _("The processing fee percentage must be greater than zero."))

    @api.constrains('requested_loan_amount')
    def _check_requested_loan_amount(self):
        """check requested loan amount"""
        for rec in self:
            if rec.requested_loan_amount <= 0:
                raise ValidationError(
                    _("The requested loan amount must be greater than zero."))

    @api.constrains('loan_amount')
    def _check_loan_amount(self):
        """check loan amount"""
        for rec in self:
            if rec.status != 'draft' and rec.loan_amount <= 0:
                raise ValidationError(
                    _("The approved loan amount must be greater than zero."))
            elif rec.loan_amount > rec.requested_loan_amount:
                raise ValidationError(
                    _("The approved loan amount cannot be greater than the requested loan amount."))

    @api.constrains('requested_term')
    def _check_requested_term(self):
        """check requested term"""
        for rec in self:
            if rec.requested_term <= 0:
                raise ValidationError(
                    _("The requested term must be greater than zero."))

    @api.constrains('term')
    def _check_term(self):
        """check term"""
        for rec in self:
            if rec.status != 'draft' and rec.term <= 0:
                raise ValidationError(
                    _("The approved term must be greater than zero."))

    @api.constrains('terms_and_conditions', 'repayment_terms')
    def _check_terms_and_conditions_and_repayment_terms(self):
        """check terms and conditions and repayment terms"""
        for rec in self:
            if rec.status != 'draft' and is_html_empty(rec.terms_and_conditions):
                raise ValidationError(
                    _("Invalid field terms & conditions.\nPlease add terms and conditions."))
            if rec.status != 'draft' and is_html_empty(rec.repayment_terms):
                raise ValidationError(
                    _("Invalid field repayment terms.\nPlease add repayment terms."))

    @api.constrains('start_date', 'app_date', )
    def _check_start_date(self):
        """check loan expected start date"""
        for rec in self:
            start_date = rec.start_date
            approval_date = rec.approval_date
            if (
                    rec.status != 'draft' and start_date and approval_date and start_date < approval_date):
                raise ValidationError(
                    _("The start date cannot be earlier than the application date or approval date")
                )

    @api.constrains('installment_start_date')
    def _check_installment_start_date(self):
        """check installment start date"""
        for rec in self:
            if (rec.status != 'draft' and rec.app_date and rec.installment_start_date and
                    rec.installment_start_date < rec.app_date):
                raise ValidationError(
                    _(f"The installment start date cannot be the same as or earlier than the "
                      f"application date."))

    @api.constrains('penalty_amount', 'penalty_percentage', 'penalty_type', 'is_penalty')
    def _check_penalty_amount_percentage(self):
        """check penalty amount and penalty percentage"""
        for rec in self:
            if rec.status != 'draft' and rec.is_penalty:
                if rec.penalty_type == 'fixed' and rec.penalty_amount <= 0:
                    raise ValidationError(
                        _("Penalty amount must be greater than zero."))
                if rec.penalty_type == 'percentage' and rec.penalty_percentage <= 0:
                    raise ValidationError(
                        _("Penalty percentage must be greater than zero."))

    @api.constrains('is_fee', 'fee_amount')
    def _validate_fee_amount(self):
        """
        Method to check that if there installment fee than
        """
        for rec in self:
            if rec.is_fee and rec.fee_amount <= 0:
                raise ValidationError(_("The value for fee amount should not be zero and less."))

    @api.constrains('requested_start_date')
    def _check_requested_start_date(self):
        """check loan expected start date"""
        for rec in self:
            if (
                    rec.app_date and rec.requested_start_date and rec.requested_start_date < rec.app_date):
                raise ValidationError(
                    _(f"The expected start date cannot be the same as or earlier than the "
                      f"application date."))

    @api.constrains('is_grace_period', 'grace_period')
    def _check_grace_period_value(self):
        """
        Method to verify that grace period is grater that zero
        """
        for rec in self:
            if rec.is_grace_period and rec.grace_period < 1:
                raise ValidationError(_("Grace period can't be zero or less."))

    @api.constrains('approval_date')
    def _check_approval_date(self):
        """
        Check value for approval date
        """
        for rec in self:
            approval_date = rec.approval_date
            app_date = rec.app_date
            if approval_date and approval_date < app_date:
                raise ValidationError(_("Approval date can't be earlier than application date."))

    @api.model_create_multi
    def create(self, vals_list):
        """Create method"""
        res = super().create(vals_list)
        for rec in res:
            rec.name = self.env['ir.sequence'].next_by_code(
                'customer.loan.sequence') or 'New'
            rec.access_token = secrets.token_urlsafe(16)
        return res

    @api.model
    def _cron_send_installment_reminder_create_invoice(self):
        """cron send installment reminder to customer and create invoice for installment"""

        installment_due_days = self.env['ir.config_parameter'].sudo().get_param(
            'tk_loan_management.installment_reminder_days')

        loans = self.search([('status', '=', 'in_progress')])
        for loan in loans:

            if (not loan.bank_cash_account
                    or not loan.receivable_account_id
                    or not loan.interest_income_account_id
                    or not loan.repayment_journal_item_id or not loan.loan_lines_ids):
                continue

            loan_installments = self.env['customer.loan.lines'].search(
                [('customer_loan_id', '=', loan.id), ('emi_date', '!=', False)],
                order="emi_date ASC")
            for installment in loan_installments:
                today = fields.Date.today()

                due_date = installment.emi_date - timedelta(
                    days=int(installment_due_days))

                if not installment.journal_entry_id and today >= due_date:
                    journal_lines = [(0, 0, {
                        'partner_id': loan.env.company.partner_id.id,
                        'account_id': loan.bank_cash_account.id,
                        'debit': installment.total_installment_amount
                    }), (0, 0, {
                        'partner_id': loan.customer_id.id,
                        'account_id': loan.receivable_account_id.id,
                        'credit': installment.installment_amount
                    }), (0, 0, {
                        'partner_id': loan.customer_id.id,
                        'account_id': loan.interest_income_account_id.id,
                        'credit': installment.total_installment_amount - installment.installment_amount
                    })]

                    journal_entry_id = self.env['account.move'].create({
                        'journal_id': loan.repayment_journal_item_id.id,
                        'ref': installment.installments_no,
                        'move_type': 'entry',
                        'customer_loan_id': loan.id,
                        'loan_line_id': installment.id,
                        'line_ids': journal_lines
                    })

                    loan.current_installment_amount = (
                        installment.total_installment_amount)
                    loan.current_installment_due_date = installment.emi_date

                    installment.journal_entry_id = journal_entry_id.id

                    mail_template = self.env.ref(
                        'tk_loan_management.installment_reminder_mail_template'
                    )
                    if mail_template:
                        mail_template.send_mail(
                            loan.id, force_send=True,
                            email_values={
                                'author_id': loan.company_id.partner_id.id})

                    body = Markup(
                        f'<strong>An installment reminder email has been sent to the '
                        f'customer.</strong><br/>')
                    author = loan.company_id.partner_id.id
                    partner = loan.responsible_id.id
                    loan.message_post(
                        body=body, message_type="email",
                        author_id=author, partner_ids=[partner]
                    )

    @api.model
    def _cron_installment_due_penalty(self):
        """cron installment due penalty"""

        loans = self.search([('status', '=', 'in_progress')])

        for loan in loans:
            if (not loan.loan_lines_ids
                    or not loan.is_penalty
                    or not loan.bank_cash_account
                    or not loan.receivable_account_id
                    or not loan.interest_income_account_id
                    or not loan.repayment_journal_item_id):
                continue

            loan_installments = self.env['customer.loan.lines'].search(
                [('customer_loan_id', '=', loan.id), ('journal_entry_id', '!=', False)],
                order="emi_date ASC")

            od_installment_lines = []
            previous_installment_ids = []

            for installment in loan_installments:
                today = fields.Date.today()
                penalty = self.calculate_penalty(loan, installment)

                if (installment.journal_entry_id.state != 'posted' and
                        today > installment.emi_date
                        and not installment.penalty_journal_entry_id):

                    journal_lines = [(0, 0, {
                        'partner_id': loan.env.company.partner_id.id,
                        'account_id': loan.bank_cash_account.id,
                        'tax_ids': loan.penalty_tax_ids,
                        'name': f"Penalty of {installment.installments_no} overdue",
                        'debit': penalty
                    }), (0, 0, {
                        'partner_id': loan.customer_id.id,
                        'account_id': loan.interest_income_account_id.id,
                        'tax_ids': loan.penalty_tax_ids,
                        'name': f"Penalty of {installment.installments_no} overdue",
                        'credit': penalty
                    })]
                    if od_installment_lines:
                        journal_lines.extend(od_installment_lines)

                    journal_entry_id = self.env['account.move'].create({
                        'journal_id': loan.repayment_journal_item_id.id,
                        'ref': f"Penalty of {installment.installments_no} overdue",
                        'move_type': 'entry',
                        'customer_loan_id': loan.id,
                        'customer_installment_id': installment.journal_entry_id.id,
                        'line_ids': journal_lines
                    })

                    loan.penalty_lines_ids = [
                        (0, 0, {'penalty': f'Penalty on {installment.installments_no}',
                                'installment_amount': installment.total_installment_amount,
                                'penalty_amount': journal_entry_id.amount_total,
                                'journal_entry_id': journal_entry_id.id,
                                })]
                    installment.penalty_journal_entry_id = journal_entry_id.id
                    installment.installment_od_count = 1

                    for p_installment in previous_installment_ids:
                        previous_installment = self.env['customer.loan.lines'].search(
                            [('id', '=', p_installment)])
                        previous_installment.installment_od_count += 1

                    body = Markup(
                        f'<strong>Penalty for overdue installment email sent to the '
                        f'customer.</strong><br/>')
                    author = loan.company_id.partner_id.id
                    partner = loan.responsible_id.id
                    loan.message_post(body=body, message_type="email",
                                      author_id=author, partner_ids=[partner])

                    mail_template = self.env.ref(
                        'tk_loan_management.installment_overdue_penalty_mail_template'
                    )
                    if mail_template:
                        mail_template.send_mail(
                            loan.id, force_send=True,
                            email_values={
                                'author_id': loan.company_id.partner_id.id})

                elif (installment.journal_entry_id.state != 'posted' and
                      today > installment.emi_date
                      and installment.penalty_journal_entry_id):

                    od_installment_lines += [(0, 0, {
                        'partner_id': loan.env.company.partner_id.id,
                        'account_id': loan.bank_cash_account.id,
                        'tax_ids': loan.penalty_tax_ids,
                        'name': f"Penalty of {installment.installments_no} overdue",
                        'debit': penalty
                    }), (0, 0, {
                        'partner_id': loan.customer_id.id,
                        'account_id': loan.interest_income_account_id.id,
                        'tax_ids': loan.penalty_tax_ids,
                        'name': f"Penalty of {installment.installments_no} overdue",
                        'credit': penalty
                    })]
                    compound_interest = (
                        self.calculate_compound_interest_test(loan, penalty,
                                                              installment.installment_od_count))
                    if compound_interest > 0 and loan.penalty_type == 'percentage':
                        od_installment_lines += [(0, 0, {
                            'partner_id': loan.env.company.partner_id.id,
                            'account_id': loan.bank_cash_account.id,
                            'name': f"Interest of {installment.installments_no} overdue penalty",
                            'tax_ids': loan.penalty_tax_ids,
                            'is_cst_penalty_on_penalty': True,
                            'debit': compound_interest
                        }), (0, 0, {
                            'partner_id': loan.customer_id.id,
                            'account_id': loan.interest_income_account_id.id,
                            'name': f"Interest of {installment.installments_no} overdue penalty",
                            'tax_ids': loan.penalty_tax_ids,
                            'is_cst_penalty_on_penalty': True,
                            'credit': compound_interest
                        })]
                        previous_installment_ids.append(installment.id)

                elif (installment.journal_entry_id.state == 'posted' and
                      today > installment.emi_date and
                      installment.penalty_journal_entry_id.state != 'posted'):

                    compound_interest = (
                        self.calculate_compound_interest_test(loan, penalty,
                                                              installment.installment_od_count))
                    if compound_interest > 0 and loan.penalty_type == 'percentage':
                        od_installment_lines += [(0, 0, {
                            'partner_id': loan.env.company.partner_id.id,
                            'account_id': loan.bank_cash_account.id,
                            'name': f"Interest of {installment.installments_no} overdue penalty",
                            'tax_ids': loan.penalty_tax_ids,
                            'is_cst_penalty_on_penalty': True,
                            'debit': compound_interest
                        }), (0, 0, {
                            'partner_id': loan.customer_id.id,
                            'account_id': loan.interest_income_account_id.id,
                            'name': f"Interest of {installment.installments_no} overdue penalty",
                            'tax_ids': loan.penalty_tax_ids,
                            'is_cst_penalty_on_penalty': True,
                            'credit': compound_interest
                        })]
                        previous_installment_ids.append(installment.id)

    @api.model
    def _cron_loan_overdue_penalty(self):
        """cron loan overdue penalty"""
        today = fields.Date.today()
        loans = self.search(
            [('status', '=', 'in_progress'), ('end_date', '<', today)])

        for loan in loans:
            if (not loan.loan_lines_ids
                    or not loan.is_penalty
                    or not loan.bank_cash_account
                    or not loan.receivable_account_id
                    or not loan.interest_income_account_id
                    or not loan.repayment_journal_item_id):
                continue

            journal_lines = []
            previous_installment_ids = []
            od_installment_lines = []

            today = fields.Date.today()
            diff = relativedelta(today, loan.end_date)
            months_difference = (diff.years * 12) + diff.months
            quarters_difference = months_difference // 3
            years_difference = diff.years

            installment_type = {'monthly': months_difference, 'quarterly': quarters_difference,
                                'yearly': years_difference}
            duration = installment_type.get(loan.installment_type)

            if loan.loan_od_count >= duration:
                continue

            installment_total_amount = 0

            for installment in loan.loan_lines_ids:
                penalty = self.calculate_penalty(loan, installment)

                if installment.journal_entry_id.state != 'posted':
                    journal_lines += [(0, 0, {
                        'partner_id': loan.env.company.partner_id.id,
                        'account_id': loan.bank_cash_account.id,
                        'tax_ids': loan.penalty_tax_ids,
                        'name': f"Penalty of {installment.installments_no} overdue",
                        'debit': penalty
                    }), (0, 0, {
                        'partner_id': loan.customer_id.id,
                        'account_id': loan.interest_income_account_id.id,
                        'tax_ids': loan.penalty_tax_ids,
                        'name': f"Penalty of {installment.installments_no} overdue",
                        'credit': penalty
                    })]
                    compound_interest = (
                        self.calculate_compound_interest_test(loan, penalty,
                                                              installment.installment_od_count))
                    if compound_interest > 0 and loan.penalty_type == 'percentage':
                        journal_lines += [(0, 0, {
                            'partner_id': loan.env.company.partner_id.id,
                            'account_id': loan.bank_cash_account.id,
                            'tax_ids': loan.penalty_tax_ids,
                            'is_cst_penalty_on_penalty': True,
                            'name': f"Interest of {installment.installments_no} overdue penalty",
                            'debit': compound_interest
                        }), (0, 0, {
                            'partner_id': loan.customer_id.id,
                            'account_id': loan.interest_income_account_id.id,
                            'tax_ids': loan.penalty_tax_ids,
                            'is_cst_penalty_on_penalty': True,
                            'name': f"Interest of {installment.installments_no} overdue penalty",
                            'credit': compound_interest
                        })]
                        previous_installment_ids.append(installment.id)
                    installment_total_amount += installment.total_installment_amount

                elif (installment.journal_entry_id.state == 'posted' and
                      installment.emi_date and
                      today > installment.emi_date and
                      installment.penalty_journal_entry_id.state != 'posted'):

                    compound_interest = (
                        self.calculate_compound_interest_test(loan, penalty,
                                                              installment.installment_od_count))
                    if compound_interest > 0 and loan.penalty_type == 'percentage':
                        od_installment_lines += [(0, 0, {
                            'partner_id': loan.env.company.partner_id.id,
                            'account_id': loan.bank_cash_account.id,
                            'tax_ids': loan.penalty_tax_ids,
                            'is_cst_penalty_on_penalty': True,
                            'name': f"Interest of {installment.installments_no} overdue penalty",
                            'debit': compound_interest
                        }), (0, 0, {
                            'partner_id': loan.customer_id.id,
                            'account_id': loan.interest_income_account_id.id,
                            'tax_ids': loan.penalty_tax_ids,
                            'is_cst_penalty_on_penalty': True,
                            'name': f"Interest of {installment.installments_no} overdue penalty",
                            'credit': compound_interest
                        })]
                        previous_installment_ids.append(installment.id)
                    installment_total_amount += installment.total_installment_amount

            loan.loan_od_count += 1

            if od_installment_lines:
                journal_lines.extend(od_installment_lines)

            journal_entry_id = self.env['account.move'].create({
                'journal_id': loan.repayment_journal_item_id.id,
                'ref': loan.name,
                'move_type': 'entry',
                'customer_loan_id': loan.id,
                'line_ids': journal_lines
            })

            loan.penalty_lines_ids = [
                (0, 0, {'penalty': f'Loan overdue penalty',
                        'installment_amount': installment_total_amount,
                        'penalty_amount': journal_entry_id.amount_total,
                        'journal_entry_id': journal_entry_id.id,
                        })]
            installment_total_amount = 0
            for p_installment in previous_installment_ids:
                previous_installment = self.env['customer.loan.lines'].search(
                    [('id', '=', p_installment)])
                previous_installment.installment_od_count += 1

            body = Markup(
                f'<strong>Penalty for overdue installment email sent to the '
                f'customer.</strong><br/>')
            author = loan.company_id.partner_id.id
            partner = loan.responsible_id.id
            loan.message_post(body=body, message_type="email",
                              author_id=author, partner_ids=[partner])

            mail_template = self.env.ref(
                'tk_loan_management.installment_overdue_penalty_mail_template'
            )
            if mail_template:
                mail_template.send_mail(loan.id, force_send=True,
                                        email_values={'author_id': loan.company_id.partner_id.id})

    @api.model
    def _cron_add_overdue_interest(self):
        """
        Cron method to add overdue interest into installment
        """
        active_loans = self.env['customer.loan'].sudo().search([
            ('status', '=', 'in_progress')
        ])
        today_date = datetime.date.today()

        for loan in active_loans:
            penalty_interest_rate = loan.od_penalty_interest
            if loan.is_overdue_penalty_interest and penalty_interest_rate > 0.0:
                overdue_installments = loan.loan_lines_ids.filtered(
                    lambda line: line.emi_date < today_date and line.status != 'paid')
                for i in overdue_installments:
                    old_overdue_penalty = i.penalty_interest
                    overdue_interest = 10 + penalty_interest_rate
                    late_days = (today_date - i.emi_date).days

                    penalty_interest = self._get_overdue_installment_interest(
                        i.total_installment_amount - old_overdue_penalty, overdue_interest,
                        late_days)
                    i.write({
                        "penalty_interest": penalty_interest
                    })
                    total_installment_amount = i.total_installment_amount - old_overdue_penalty + penalty_interest
                    i.total_installment_amount = total_installment_amount

    def _get_overdue_installment_interest(self, overdue_amount, annual_rate, late_days):
        """
        Method to get overdue installment interest
        """
        late_interest = overdue_amount * (annual_rate / 100) * (late_days / 360)
        return round(late_interest, 2)

    def calculate_compound_interest_test(self, loan, penalty_principal, times):
        """calculate compound interest"""
        current_penalty_compound_interest = 0
        previous_penalty_compound_interest = 0
        actual_compound_interest = 0

        year_divison = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
        time_divison = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
        year = year_divison.get(loan.installment_type, 1)
        time_d = time_divison.get(loan.installment_type, 1)

        if penalty_principal > 0 and times:
            current_penalty_compound_interest = (penalty_principal * (
                    1 + (loan.penalty_percentage / 100) / year) ** (
                                                         year * (
                                                         times / time_d))) - penalty_principal
            if times and times > 1:
                previous_times = times - 1
                previous_penalty_compound_interest = (penalty_principal * (
                        1 + (loan.penalty_percentage / 100) / year) ** (year * (
                        previous_times / time_d))) - penalty_principal
            actual_compound_interest = (
                current_penalty_compound_interest
                if previous_penalty_compound_interest < 0
                else current_penalty_compound_interest - previous_penalty_compound_interest
            )

        return actual_compound_interest

    def calculate_penalty(self, loan, installment):
        """calculate penalty"""
        penalty = 0
        if loan.penalty_type == 'fixed':
            penalty = loan.penalty_amount
        if loan.penalty_type == 'percentage':
            penalty = (installment.total_installment_amount *
                       loan.penalty_percentage) / 100

        return penalty

    def update_dict_overdue_penalty(self, loan):
        """update dict overdue penalty"""
        dict_overdue_penalty = {}
        for overdue_penalty in loan.penalty_lines_ids:
            if overdue_penalty.invoice_id.payment_state not in [
                'paid', 'in_payment']:
                if f"Penalty of {overdue_penalty.penalty}" not in dict_overdue_penalty.keys():
                    dict_overdue_penalty[f"Penalty of {overdue_penalty.penalty}"] = 1

                for overdue_penalty_lines in overdue_penalty.invoice_id.invoice_line_ids:
                    if (overdue_penalty_lines.is_cst_principle_penalty and
                            overdue_penalty_lines.name in dict_overdue_penalty.keys()):
                        dict_overdue_penalty[overdue_penalty_lines.name] += 1
        return dict_overdue_penalty

    def calculate_compound_interest(self, filter_overdue_penalty, filter_overdue_penalty_id,
                                    dict_overdue_penalty,
                                    overdue_penalty, loan, plus=False, years_plus=1):
        """calculate compound interest"""
        penalty_principal = 0
        current_penalty_compound_interest = 0
        previous_penalty_compound_interest = 0
        actual_compound_interest = 0

        year_divison = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
        time_divison = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
        year = year_divison.get(loan.installment_type, 1)
        time_d = time_divison.get(loan.installment_type, 1)

        penalties = dict(zip(filter_overdue_penalty,
                             filter_overdue_penalty_id))

        for name, penalty_id in penalties.items():
            times = dict_overdue_penalty.get(f"{name} penalty")
            if times is None:
                times = 1
            if plus:
                times += years_plus
            penalty_principal = self.env['account.move.line'].search(
                [('id', '=', penalty_id), ('name', '=', name)]).price_total
            if (penalty_principal > 0 and times and
                    f"Penalty of {overdue_penalty.penalty}" == f"{name} penalty"):
                current_penalty_compound_interest = (penalty_principal * (
                        1 + (loan.penalty_percentage / 100) / year) ** (
                                                             year * (
                                                             times / time_d))) - penalty_principal
                if times and times > 1:
                    previous_times = times - 1
                    previous_penalty_compound_interest = (penalty_principal * (
                            1 + (loan.penalty_percentage / 100) / year) ** (year * (
                            previous_times / time_d))) - penalty_principal
                actual_compound_interest = (
                    current_penalty_compound_interest
                    if previous_penalty_compound_interest < 0
                    else current_penalty_compound_interest - previous_penalty_compound_interest
                )

        return actual_compound_interest, penalty_principal

    def reset_installments(self):
        """reset installments"""
        self.loan_lines_ids = [(5, 0, 0)]
        self.interest_amount = 0
        self.interest_rate = 0

    def compute_installment(self):
        """Compute installment amount and schedule."""

        if not self.approval_date:
            return display_message(_("Missing approval date"),
                                   _("Please enter approval date before creating installment."))

        if self.loan_amount <= 0:
            return display_message(_("Invalid loan amount."),
                                   "Loan amount must be greater than zero.")
        if self.term <= 0:
            return display_message(_("Invalid term."),
                                   "Loan term must be greater than zero.")
        if not self.approved_loan_type_id:
            return display_message(_("Invalid Loan Type."),
                                   _("Please select type before computing installment."))
        if not self.start_date:
            return display_message(_("Invalid Start Date."),
                                   _("Please select a start date before computing installment."))
        if self.is_initial_fee and self.initial_fee_amount < 1:
            return display_message(_("Invalid Initial Fee."),
                                   _("Initial fee should be greater than zero."))

        self.interest_rate = self._get_interest_rate()

        self.installment_amount, total_amount = self._calculate_emi(
            self.loan_amount,
            self.interest_rate,
            self.term,
            self.installment_type,
            self.is_grace_period
        )

        # Add fee into installment amount if applicable
        fee = 0.0
        if self.is_fee:
            fee_per = self.fee_amount
            fee = fee_per * self.loan_amount / 100

        self.interest_amount = 0
        start_date = self.installment_start_date or False
        self.loan_lines_ids = [(5, 0, 0)]  # Clear existing lines
        self._generate_loan_schedule(start_date, total_amount, fee=fee)

    def _get_interest_rate(self):
        """Get the closest matching interest rate based on term and installment type."""
        if self.approved_loan_type_id.term_lines_ids:
            durations = self.env['customer.loan.type.term.lines'].search([
                ('loan_type_id', '=', self.approved_loan_type_id.id),
                ('installment_type', '=', self.installment_type)
            ]).mapped('duration')
            if durations:
                closest_duration = min(
                    durations, key=lambda x: abs(x - self.term))
                return self.env['customer.loan.type.term.lines'].search([
                    ('duration', '=', closest_duration),
                    ('loan_type_id', '=', self.approved_loan_type_id.id),
                    ('installment_type', '=', self.installment_type)
                ]).interest_rate
            else:
                return self.approved_loan_type_id.interest_rate
        elif self.approved_loan_type_id.is_interest:
            return self.approved_loan_type_id.interest_rate
        return 0

    def _calculate_emi(self, loan_amount, interest_rate, term, installment_type, is_grace_period):
        """Calculate EMI and total amount based on loan details."""
        periods_per_year = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
        periods = periods_per_year.get(installment_type, 12)
        rate_per_period = interest_rate / periods / 100
        if is_grace_period:
            term -= self.grace_period

        if rate_per_period != 0:
            emi = round(
                (loan_amount * rate_per_period * (1 + rate_per_period) ** term) / (
                        (1 + rate_per_period) ** term - 1), 2
            )
        else:
            emi = loan_amount / term

        total_amount = round(emi * term, 2)

        return emi, total_amount

    def _generate_loan_schedule(self, start_date, total_amount, fee):
        """Generate loan schedule and populate loan lines."""
        total_remaining_amount = total_amount
        principal_balance = self.loan_amount
        periods_per_month = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
        step_months = periods_per_month.get(self.installment_type, 1)
        relative_months_step = {'monthly': 1, 'quarterly': 3, 'yearly': 12}
        relative_months = relative_months_step.get(self.installment_type, 1)
        installment_day = start_date.day
        installment_target_date = start_date

        # find holiday dates
        holiday_dates = self._get_public_holiday_dates()

        # Grace period
        grace_period = 0
        if self.is_grace_period:
            grace_period = self.grace_period

        for i in range(1, self.term + 1):
            installment_date = self._get_valid_installment_date(target_date=installment_target_date,
                                                                holiday_dates=holiday_dates)
            interest_amount = round(
                (principal_balance * self.interest_rate) / step_months / 100, 2)

            total_installment_amount = self.installment_amount

            if i == 1:
                approval_date = self.approval_date
                installment_start_date = self.installment_start_date
                if approval_date < installment_start_date:
                    days = (installment_start_date - approval_date).days
                    interest_amount = round(
                        (principal_balance * self.interest_rate * days) / 36000, 2
                    )

            self.interest_amount += interest_amount

            if fee > 0.0:
                total_installment_amount += fee

            is_initial_fee = self.is_initial_fee
            if i == 1 and is_initial_fee:
                fee_per = self.initial_fee_amount
                initial_fee = fee_per * self.loan_amount / 100

                total_installment_amount += initial_fee
                installment_no = f'Installment {i} + Initial Fee ({self.currency_id.symbol}{initial_fee})'
            else:
                installment_no = f'Installment {i}'

            if i <= grace_period:
                total_installment_amount = total_installment_amount - self.installment_amount + interest_amount
                self.loan_lines_ids = [(0, 0, {
                    'installments_no': installment_no,
                    'emi_date': installment_date.strftime(
                        '%Y-%m-%d') if installment_date else False,
                    'installment_amount': 0.0,
                    'total_installment_amount': total_installment_amount,
                    'interest_amount': interest_amount,
                    'remaining_amount': total_remaining_amount,
                    'principal_balance': principal_balance,
                    'is_grace_installment': True,
                    'fee_amount': fee
                })]

                if installment_target_date:
                    installment_target_date = self._get_new_valid_target_date(
                        old_target_date=installment_target_date, installment_day=installment_day,
                        relative_months=relative_months)
                continue

            principal_payment = round(
                self.installment_amount - interest_amount, 2
            )
            principal_balance -= principal_payment
            total_remaining_amount -= self.installment_amount

            if i == self.term and principal_balance < 0:
                principal_payment += principal_balance
                total_installment_amount += principal_balance
                principal_balance = 0

            elif i == self.term and principal_balance > 0:
                if round(total_remaining_amount, 2) != 0:
                    total_remaining_amount -= principal_balance
                principal_payment += principal_balance
                total_installment_amount += principal_balance
                principal_balance = 0

            self.loan_lines_ids = [(0, 0, {
                'installments_no': installment_no,
                'emi_date': installment_date.strftime('%Y-%m-%d') if installment_date else False,
                'installment_amount': principal_payment,
                'total_installment_amount': total_installment_amount,
                'interest_amount': interest_amount,
                'remaining_amount': total_remaining_amount,
                'principal_balance': principal_balance,
                'fee_amount': fee
            })]

            if installment_target_date:
                installment_target_date = self._get_new_valid_target_date(
                    old_target_date=installment_target_date, installment_day=installment_day,
                    relative_months=relative_months
                )

    def _get_public_holiday_dates(self):
        """
        Method to get public holiday dates
        """
        holiday_dates = set()
        holidays = self.env['public.holidays'].search([
            ('status', '=', 'confirmed')
        ])
        for holiday in holidays:
            start = holiday.start_date
            end = holiday.end_date or holiday.start_date
            delta = (end - start).days
            for i in range(delta + 1):
                holiday_dates.add(start + timedelta(days=i))

        return holiday_dates

    def _get_valid_installment_date(self, target_date, holiday_dates):
        """
        Adjusts the target_date backward if it falls on Sunday or in a public holiday.
        """
        while target_date.weekday() == 6 or target_date in holiday_dates:
            target_date -= timedelta(days=1)
        return target_date

    def _get_new_valid_target_date(self, old_target_date, installment_day, relative_months):
        """
        :param old_target_date:
        :return new_target_date
        """
        # Move to the next installment month
        old_target_date += relativedelta(months=relative_months)

        # Get the last valid day of the target month
        year = old_target_date.year
        month = old_target_date.month
        last_day_of_month = monthrange(year, month)[1]

        # Choose the smaller of original installment day or last day of the month
        adjusted_day = min(installment_day, last_day_of_month)

        # Replace the day (safe)
        return old_target_date.replace(day=adjusted_day)

    def action_recalculate_installment(self):
        """
        Method to recalculate the installment
        """
        if self.credit_balance <= 0:
            return display_message(
                title=_("Invalid operation"),
                message=_("You cannot recalculate installments while credit balance is zero.")
            )

        remain_installment = self.env['customer.loan.lines'].sudo().search([
            ('customer_loan_id', '=', self.id),
            ('status', '=', 'unpaid'),
            ('is_grace_installment', '=', False)
        ])

        if len(remain_installment) < 2:
            return None

        paid_installment_count = len(
            self.loan_lines_ids.filtered(
                lambda
                    line: line.status == 'paid' and not line.is_grace_installment and not line.is_prepayment_line))

        loan_amount = self.remaining_loan_principle_amount - self.credit_balance
        term = len(remain_installment)

        self.interest_rate = self._get_interest_rate()

        # Add fee into installment amount if applicable
        self.installment_amount, total_amount = self._calculate_emi(
            loan_amount,
            self.interest_rate,
            term,
            self.installment_type,
            is_grace_period=False
        )
        fee = 0.0
        if self.is_fee:
            fee_per = self.fee_amount
            fee = fee_per * self.loan_amount / 100

        self.interest_amount = 0

        # Take the first remain installment date as a start date
        start_date = remain_installment[0].emi_date

        # Clear all the remain installment lines
        remain_installment.unlink()

        prepayment_line = self.env['customer.loan.lines'].create({
            'installments_no': 'Principal Prepayment',
            'emi_date': fields.Date.today(),
            'installment_amount': self.credit_balance,
            'total_installment_amount': self.credit_balance,
            'interest_amount': 0.0,
            'remaining_amount': 0.0,
            'customer_loan_id': self.id,
            'is_prepayment_line': True,
            'principal_balance': loan_amount,
            'fee_amount': 0.0
        })

        # Prepayment journal
        journal_lines = [
            (0, 0, {
                'partner_id': self.customer_id.id,
                'account_id': self.receivable_account_id.id,
                'name': "Principal Amount",
                'is_principal': True,
                'credit': self.credit_balance
            }),
            (0, 0, {
                'partner_id': self.env.company.partner_id.id,
                'account_id': self.bank_cash_account.id,
                'name': "Principal Amount",
                'is_principal': True,
                'debit': self.credit_balance
            })
        ]

        journal_item = self.repayment_journal_item_id
        journal_entry_id = self.env['account.move'].create({
            'journal_id': journal_item.id,
            'ref': 'Principal Prepayment',
            'move_type': 'entry',
            'customer_loan_id': self.id,
            'loan_line_id': prepayment_line.id,
            'line_ids': journal_lines
        })
        journal_entry_id.action_post()

        # Get new installments
        installments = self._generate_recalculated_installment(start_date, total_amount, fee,
                                                               paid_installment_count, term)

        self.write({
            "loan_lines_ids": installments,
            "send_recalculate_inst_mail": True
        })

        self.remaining_loan_principle_amount = self.remaining_loan_principle_amount - self.credit_balance

        self.credit_balance = 0.0

    def _generate_recalculated_installment(self, start_date, total_amount, fee, paid_inst_count,
                                           term):
        """
        Method to generate new recalculated installments
        """
        total_remaining_amount = total_amount
        principal_balance = self.remaining_loan_principle_amount
        periods_per_month = {'monthly': 12, 'quarterly': 4, 'yearly': 1}
        step_months = periods_per_month.get(self.installment_type, 1)
        relative_months_step = {'monthly': 1, 'quarterly': 3, 'yearly': 12}
        relative_months = relative_months_step.get(self.installment_type, 1)
        installment_day = start_date.day
        installment_target_date = start_date

        # find holiday dates
        holiday_dates = self._get_public_holiday_dates()

        # # Grace period
        # grace_period = 0
        # if self.is_grace_period:
        #     grace_period = self.grace_period

        installment_no = paid_inst_count + 1 + (self.grace_period if self.is_grace_period else 0)

        installments = []

        for i in range(1, term + 1):
            installment_date = self._get_valid_installment_date(target_date=installment_target_date,
                                                                holiday_dates=holiday_dates)
            interest_amount = round(
                (principal_balance * self.interest_rate) / step_months / 100, 2)

            total_installment_amount = self.installment_amount

            self.interest_amount += interest_amount

            if fee > 0.0:
                total_installment_amount += fee

            installment_no_str = f'Installment {installment_no}'

            principal_payment = round(
                self.installment_amount - interest_amount, 2
            )
            principal_balance -= principal_payment
            total_remaining_amount -= self.installment_amount

            if i == term and principal_balance < 0:
                principal_payment += principal_balance
                total_installment_amount += principal_balance
                principal_balance = 0

            elif i == term and principal_balance > 0:
                if round(total_remaining_amount, 2) != 0:
                    total_remaining_amount -= principal_balance
                principal_payment += principal_balance
                total_installment_amount += principal_balance
                principal_balance = 0

            line = (0, 0, {
                'installments_no': installment_no_str,
                'emi_date': installment_date.strftime('%Y-%m-%d') if installment_date else False,
                'installment_amount': principal_payment,
                'total_installment_amount': total_installment_amount,
                'interest_amount': interest_amount,
                'remaining_amount': total_remaining_amount,
                'principal_balance': principal_balance,
                'fee_amount': fee
            })

            installments.append(line)

            installment_no += 1

            if installment_target_date:
                installment_target_date = self._get_new_valid_target_date(
                    old_target_date=installment_target_date, installment_day=installment_day,
                    relative_months=relative_months
                )

        return installments

    def action_send_recalculate_mail(self):
        """
        Method to send recalculated installment mail
        """
        mail_template = self.env.ref(
            'tk_loan_management.revised_installment_schedule'
        )
        if mail_template:
            mail_template.send_mail(
                self.id, force_send=True,
                email_values={
                    'author_id': self.company_id.partner_id.id})
            self.write({
                "send_recalculate_inst_mail": False
            })

    def create_attachment(self, name, report_action, res_id):
        """create attachment"""
        pdf_data = self.env['ir.actions.report']._render_qweb_pdf(report_action, res_ids=[res_id])[
            0]
        b64_pdf = base64.b64encode(pdf_data)

        return self.env['ir.attachment'].create({
            'name': name,
            'type': 'binary',
            'datas': b64_pdf,
            'store_fname': name,
            'res_model': self._name,
            'res_id': res_id,
            'mimetype': 'application/pdf'
        })

    def _send_loan_confirmation_email_to_customer(self):
        """Send loan confirmation email to customer"""
        mail_template = self.env.ref(
            'tk_loan_management.sanction_letter_mail_template')
        if not self.email:
            raise ValidationError(
                _(f"Before sending the email to the customer, "
                  f"please ensure the customer's email address is added."))

        if mail_template:
            mail_template.send_mail(self.id, force_send=True,
                                    email_values={'author_id': self.company_id.partner_id.id})

    def send_signature_certificate_email_to_customer(self):
        """Send loan confirmation email to customer"""
        signature_attachment = (
            self.create_attachment(
                "Signature Certificate",
                'tk_loan_management.customer_loan_signature_certificate_qweb_report_action',
                self.id))
        sanction_attachment = (
            self.create_attachment(
                "Sanction Letter",
                'tk_loan_management.customer_sanction_letter_action',
                self.id))

        mail_template = self.env.ref(
            'tk_loan_management.customer_signed_loan_mail_template')
        if mail_template:
            mail_template.write(
                {'attachment_ids': [(6, 0, [signature_attachment.id, sanction_attachment.id])]})
            mail_template.send_mail(self.id, force_send=True,
                                    email_values={'author_id': self.company_id.partner_id.id})

    def action_download_settlement_letter(self):
        """action download settlement letter"""
        return self.env.ref(
            "tk_loan_management.customer_settlement_letter_report_action").report_action(self)

    def action_download_sanction_letter(self):
        """action download sanction letter"""
        return self.env.ref(
            "tk_loan_management.customer_sanction_letter_action").report_action(self)

    def action_download_signature_certificate(self):
        """Action to download the signature certificate"""
        return self.env.ref(
            "tk_loan_management.customer_loan_signature_certificate_qweb_report_action"
        ).report_action(self)

    def action_download_closure_letter(self):
        """action download closure letter"""
        return self.env.ref(
            "tk_loan_management.customer_closure_letter_report_action").report_action(self)

    def action_download_noc_letter(self):
        """action download noc letter"""
        return self.env.ref("tk_loan_management.customer_noc_letter_report_action").report_action(
            self)

    def action_open_wizard(self):
        """action open wizard for grant portal access"""
        portal_wizard = self.env['portal.wizard'].with_context(
            default_partner_ids=[self.customer_id.id]).create({})
        user = self.env['res.users'].search(
            [('partner_id', '=', self.customer_id.id)])
        if user:
            self.user_id = user.id
        return {
            'name': _('Portal Access Management'),
            'type': 'ir.actions.act_window',
            'res_model': 'portal.wizard',
            'view_mode': 'form',
            'res_id': portal_wizard.id,
            'target': 'new',
        }

    def action_confirm_stage(self):
        """action confirm stage"""
        for rec in self:
            user = self.env['res.users'].search(
                [('partner_id', '=', self.customer_id.id)])
            rec.user_id = user.id

            mail_template = self.env.ref(
                'tk_loan_management.loan_request_approved_mail_template')

            if mail_template:
                mail_template.send_mail(rec.id, force_send=True, email_values={
                    'author_id': rec.company_id.partner_id.id})

            rec.status = 'confirm'

    def action_closure(self):
        """action closure"""
        for rec in self:
            if rec.status != 'in_progress' or not rec.loan_lines_ids:
                return
            if rec.remaining_amount > 0:
                return display_message(_("The loan has not been paid"),
                                       _("Please pay the loan before closure."))
            if rec.outstanding_penalty > 0:
                return display_message(_("The penalty has not been paid"),
                                       _("Please pay the penalty before closure."))
            rec.status = 'closure'
            rec.loan_closure_date = fields.Date.today()

    def action_create_invoice(self):
        """action create invoice for processing from customer"""
        processing_fee_id = self.env['ir.config_parameter'].sudo().get_param(
            'tk_loan_management.processing_fee_id')
        processing_fee_state = self.env['ir.config_parameter'].sudo().get_param(
            'tk_loan_management.processing_fee_status')

        if not processing_fee_id:
            return display_message(_("Processing fee product is not selected"),
                                   _("Goto: Settings > Customer Loan Management > "
                                     "Processing Fee Configuration > Select item for processing fee!"))

        if self.processing_fee_amount <= 0:
            return display_message(_("Invalid processing fee"),
                                   _("processing fee must be greater than zero."))

        invoice_line = []
        if (self.status == 'disbursement' and self.processing_fee_deduct_from == 'customer'):

            invoice_line.append((0, 0, {
                'product_id': int(processing_fee_id),
                'name': self.env['product.product'].browse(int(processing_fee_id)).name,
                'quantity': 1,
                'tax_ids': self.processing_fee_tax_ids.ids,
                'price_unit': self.processing_fee_amount,
            }))

            if not invoice_line:
                return
            invoice_id = self.env['account.move'].sudo().create({
                'partner_id': self.customer_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'customer_loan_id': self.id,
                'invoice_line_ids': invoice_line
            })
            self.invoice_id = invoice_id.id
            if processing_fee_state and processing_fee_state == 'posted':
                invoice_id.action_post()
            return {
                'type': 'ir.actions.act_window',
                'name': 'Invoice',
                'res_model': 'account.move',
                'res_id': invoice_id.id,
                'view_mode': 'form',
                'target': 'current',
                'context': {'create': False},
            }

    def action_disburse_loan(self):
        """action disburse loan"""
        processing_fee_id = self.env['ir.config_parameter'].sudo().get_param(
            'tk_loan_management.processing_fee_id')

        disbursement_mail_template = self.env.ref(
            'tk_loan_management.loan_disbursement_confirmation_mail_template')

        if self.is_processing_fee and self.processing_fee_amount <= 0:
            return display_message(_("Invalid processing fee"),
                                   _("processing fee must be greater than zero."))

        if (self.is_processing_fee and self.processing_fee_deduct_from == 'customer'
                and not self.invoice_id):
            return display_message(_("Processing fee has not been paid"),
                                   _("Before disbursing the loan, the processing fee must be paid."))

        if (self.is_processing_fee and self.processing_fee_deduct_from == 'customer'
                and self.invoice_id.payment_state not in [
                    'paid', 'in_payment']):
            return display_message(
                _("Processing fee has not been paid"),
                _("Before disbursing the loan, the processing fee must be paid."))

        if not self.bank_cash_account:
            return display_message(
                _("Bank Account Missing"),
                _("To create journal entry, select bank account in loan account details."))
        if not self.receivable_account_id:
            return display_message(
                _("Account Receivable Missing"),
                _("To create journal entry, select account receivable in loan account details."))

        journal_lines = [(0, 0, {
            'partner_id': self.customer_id.id,
            'account_id': self.receivable_account_id.id,
            'debit': self.loan_amount
        }), (0, 0, {
            'partner_id': self.env.company.partner_id.id,
            'account_id': self.bank_cash_account.id,
            'credit': self.loan_amount
        })]

        if self.is_processing_fee and self.processing_fee_deduct_from == 'disbursement':
            if not self.interest_income_account_id:
                return display_message(
                    _("Interest Income Account Missing"),
                    _("To create journal entry, select interest income account in loan account details."))

            journal_lines += [(0, 0, {
                'partner_id': self.env.company.partner_id.id,
                'account_id': self.bank_cash_account.id,
                'tax_ids': self.processing_fee_tax_ids.ids,
                'debit': self.processing_fee_amount
            }), (0, 0, {
                'partner_id': self.customer_id.id,
                'account_id': self.interest_income_account_id.id,
                'tax_ids': self.processing_fee_tax_ids.ids,
                'credit': self.processing_fee_amount
            })]

        journal_entry_id = self.env['account.move'].create({
            'journal_id': self.journal_item_id.id,
            'ref': self.name,
            'move_type': 'entry',
            'customer_loan_id': self.id,
            'is_disbursement': True,
            'line_ids': journal_lines
        })
        self.journal_entry_id = journal_entry_id.id

        if disbursement_mail_template:
            disbursement_mail_template.send_mail(self.id, force_send=True, email_values={
                'author_id': self.company_id.partner_id.id})
        return None

    def action_submit_request(self):
        """action submit request"""
        for rec in self:
            if rec.requested_loan_amount <= 0:
                return display_message(_("Invalid field Loan Amount."),
                                       _("The loan amount must be greater than zero."))

            if not rec.requested_start_date:
                return display_message(
                    _("Invalid field Expected Start Date."),
                    _("The expected start date is required to submit the request."))

            if not rec.customer_loan_doc_ids:
                return display_message(
                    _("Documents is not added."),
                    _("Please add documents before submitting loan request."))

            for doc in rec.customer_loan_doc_ids:
                if not doc.document:
                    return display_message(
                        _("Invalid field document."),
                        _(f"Please submit '{doc.document_type_id.name}' before submitting "
                          f"loan request."))

            if rec.is_collateral and not rec.collateral_ids:
                return display_message(
                    _("Collateral is not added."),
                    _("Please add collateral before submitting loan request.")
                )

            for collateral in rec.collateral_ids:
                if not collateral.document:
                    return display_message(
                        _("Invalid field document in collateral."),
                        _(f"Please submit '{collateral.collateral_type_id.name}' document"
                          f" before submitting loan request.")
                    )

            if rec.requested_term <= 0:
                return display_message(_("Invalid field Term."),
                                       _("The term must be greater than zero."))

            for req_docs in rec.req_document_ids:
                if req_docs.stage == 'pending':
                    return display_message(
                        _("Requested documents are pending!"),
                        _(f"Documents of {req_docs.name} are still pending."))

            for req_cols in rec.req_collateral_ids:
                if req_cols.stage == 'pending':
                    return display_message(
                        _("Requested collateral are pending!"),
                        _(f"Collateral of {req_cols.name} are still pending."))
            rec.status = 'dept_approval'

    def action_approve_request(self):
        """action approve request"""
        for rec in self:
            if rec.status == 'dept_approval' and not self.env.user.has_group(
                    'tk_loan_management.department_manager'):
                raise ValidationError(
                    _(f"You are not allowed to approve the loan request {self.name}."))

            if rec.loan_amount <= 0:
                return display_message(_("Invalid field Loan Amount."),
                                       _("The loan amount must be greater than zero."))

            if not rec.start_date:
                return display_message(
                    _("Invalid field Start Date."),
                    _("To approve the loan request, a start date is required."))

            if rec.term <= 0:
                return display_message(
                    _("Invalid field Term."), _("The term must be greater than zero."))

            if not rec.customer_loan_doc_ids:
                return display_message(_("Documents is not added."),
                                       _("Please add documents before approving loan request."))

            for doc in rec.customer_loan_doc_ids:
                if not doc.document:
                    return display_message(
                        _("Invalid field document."),
                        _(f"Please submit {doc.document_type_id.name} before approving "
                          f"loan request."))

            if rec.is_collateral and not rec.collateral_ids:
                return display_message(
                    _("Collateral is required."),
                    _("Please submit collateral before approving loan request."))

            if is_html_empty(rec.terms_and_conditions):
                return display_message(
                    _("Terms & conditions are required to proceed."),
                    _("Please add terms & conditions before approving loan request."))

            if is_html_empty(rec.repayment_terms):
                return display_message(_("Repayment terms are required to proceed."),
                                       _("Please add repayment terms before approving loan "
                                         "request."))

            if not rec.loan_lines_ids:
                return display_message(_("Installments not created."),
                                       _('Please create installment from "Loan Evaluation".'))

            for req_docs in rec.req_document_ids:
                if req_docs.stage == 'pending':
                    return display_message(
                        _("Requested documents are pending!"),
                        _(f"Documents of {req_docs.name} are still pending."))

            for req_cols in rec.req_collateral_ids:
                if req_cols.stage == 'pending':
                    return display_message(
                        _("Requested collateral are pending!"),
                        _(f"Collateral of {req_cols.name} are still pending."))

            for doc in rec.customer_loan_doc_ids:
                if doc.status != 'verified':
                    return display_message(_("Documents verification pending."),
                                           _("All documents must be verified."))

            if rec.is_collateral and not rec.collateral_ids:
                return display_message(
                    _("Collateral is required."),
                    _("Please submit collateral before approving loan request."))

            user = self.env['res.users'].search(
                [('partner_id', '=', rec.customer_id.id)])

            if not user:
                return display_message(
                    _("User account no created."),
                    _("Create the customer's user account before sending the sanction "
                      "letter confirmation."))

            self._compute_email()

            body = Markup(f'<strong>Department Approval of Loan Request : </strong>{self.name}<br/>'
                          f'<strong>Approved By : </strong>{self.env.user.name}<br/>')

            partners = (
                [self.responsible_id.partner_id.id]
                if self.responsible_id.partner_id.id
                else None
            )
            author = rec.responsible_id.partner_id.id
            post_message(self, body, partners, author, 'loan')
            self._send_loan_confirmation_email_to_customer()
            rec.status = 'confirmation'

    def action_reset_to_draft(self):
        """action reset to draft"""
        for rec in self:
            if rec.status in ['dept_approval', 'confirmation', 'rejected', 'cancel']:
                rec.status = 'draft'
                if rec.loan_lines_ids:
                    for loan in rec.customer_loan_doc_ids:
                        loan.status = 'draft'
                        loan.validator_id = False
                        loan.reason = ""
                if rec.req_document_ids:
                    rec.req_document_ids = [5, 0, 0]

                if rec.is_collateral and rec.collateral_ids:
                    rec.collateral_ids = [5, 0, 0]
                if rec.is_collateral and rec.req_collateral_ids:
                    rec.req_collateral_ids = [5, 0, 0]

    def action_disbursement(self):
        """action disbursement"""
        for rec in self:
            if not rec.loan_lines_ids:
                return display_message(_("Missing installments"),
                                       _("Please create installment from the loan evalution."))

            if rec.status == 'confirmation':
                rec.status = 'disbursement'

    def action_in_progress(self):
        """action in progress"""
        for rec in self:
            self._check_penalty_amount_percentage()
            if not rec.journal_entry_id:
                return display_message(
                    _("The loan disbursement is pending"),
                    _("Please disburse the loan first before changing the stage to "
                      "'In Progress'."))
            if rec.journal_entry_id and rec.journal_entry_id.state != 'posted':
                return display_message(
                    _("The loan has not been disbursed."),
                    _("Please disburse the loan first before changing the stage to "
                      "'In Progress'."))
            rec.status = 'in_progress'

    def _int_to_bg_words(self, number, gender='masculine'):
        """
        Helper function to convert an integer into Bulgarian words.
        Handles gender ('masculine', 'feminine', 'neuter') for numbers 1 and 2.
        """
        if number == 0:
            return _UNITS_COMMON[0]
        # Select the correct gendered units for 1 and 2
        gender_units = {
            'masculine': _UNITS_MASCULINE,
            'feminine': _UNITS_FEMININE,
            'neuter': _UNITS_NEUTER
        }.get(gender, _UNITS_MASCULINE)
        all_units = {**_UNITS_COMMON, **gender_units}

        parts = []

        # Process numbers up to 999
        if number >= 100:
            h = number // 100
            parts.append(_HUNDREDS.get(h, f"{_UNITS_COMMON[h]}стотин"))
            number %= 100

        if number > 0:
            if parts and (number < 20 or number % 10 == 0):
                parts.append("и")
            if number < 20:
                if number in all_units:
                    parts.append(all_units[number])
                else:  # For 13-19
                    parts.append(f"{_UNITS_COMMON[number % 10]}надесет")
            else:  # For 20-99
                tens = number // 10
                units = number % 10
                parts.append(f"{_UNITS_COMMON[tens]}десет" if tens != 2 else "двадесет")
                if units > 0:
                    parts.append("и")
                    parts.append(all_units[units])
        return " ".join(parts)

    def _process_chunk(self, number, gender):
        """Processes chunks of thousands, millions, etc."""
        if number == 0: return ""

        # Thousands
        if number >= 1000:
            thousands = number // 1000
            # For thousands, "two" is always "две" (feminine) because "хиляда" is feminine
            thousands_text = "хиляда" if thousands == 1 else f"{self._int_to_bg_words(thousands, 'feminine')} хиляди"

            remainder = number % 1000
            if remainder > 0:
                remainder_text = self._int_to_bg_words(remainder, gender)
                # Add "и" (and) if the remainder is less than 100
                connector = " и " if remainder < 100 else " "
                return f"{thousands_text}{connector}{remainder_text}"
            return thousands_text

        return self._int_to_bg_words(number, gender)

    def number_to_words_generic(self, number: float) -> str:
        """
        Converts a number to Bulgarian words using a generic format for any currency:
        [integer part] цели и [hundredths part] стотни
        """

        if not isinstance(number, (int, float)):
            return "Грешка: Стойността трябва да е число."

        # Split into integer and hundredths parts
        integer_part = int(number)
        hundredths_part = round((number - integer_part) * 100)
        # --- Integer Part ---

        integer_text = self._process_chunk(integer_part, 'neuter')
        integer_unit = "цяло" if integer_part == 1 else "цели"

        # --- Hundredths Part ---
        if hundredths_part == 0:
            return f"{integer_text} {integer_unit}"
        hundredths_text = self._int_to_bg_words(hundredths_part, 'feminine')
        hundredths_unit = "стотна" if hundredths_part == 1 else "стотни"
        # --- Combine Parts ---
        return f"{integer_text} {integer_unit} и {hundredths_text} {hundredths_unit}"


class CustomerLoanLines(models.Model):
    """Customer Loan Lines"""
    _name = 'customer.loan.lines'
    _description = __doc__

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")
    display_type = fields.Selection(
        selection=[('line_section', 'Section')], default=False)
    name = fields.Text()
    emi_date = fields.Date(string="Date")

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='company_id.currency_id', string='Currency')

    invoice_id = fields.Many2one(comodel_name="account.move")
    invoice_paid_date = fields.Date(compute="_compute_invoice_paid_date")
    invoice_state = fields.Selection(related="invoice_id.state", string="Payment Status")
    installments_no = fields.Char(string="Installment No.")
    total_installment_amount = fields.Monetary(currency_field="currency_id")
    installment_amount = fields.Monetary(currency_field="currency_id")
    interest_amount = fields.Monetary(
        currency_field="currency_id", string="Interest")
    total_paid_amount = fields.Monetary(currency_field="currency_id")
    # remaining_amount = fields.Monetary(currency_field="currency_id")
    principal_balance = fields.Monetary(currency_field="currency_id")

    # for penalty
    installment_od_count = fields.Integer()
    penalty_invoice_id = fields.Many2one(comodel_name="account.move")
    penalty_journal_entry_id = fields.Many2one('account.move')
    previous_installment_id = fields.Many2one(comodel_name="customer.loan.lines")
    is_count_set = fields.Boolean(default=False)
    set_od_count = fields.Char(compute="_compute_set_od_count")
    fee_amount = fields.Monetary(string="Fee")

    # Penalty interest
    penalty_interest = fields.Monetary()
    overdue_days = fields.Integer(compute='_compute_overdue_days')

    # Journal Entry
    journal_entry_id = fields.Many2one('account.move')

    # Journal entry ids

    # remaining_amount = fields.Monetary(currency_field="currency_id")
    journal_entry_ids = fields.One2many(comodel_name='account.move', inverse_name='loan_line_id',
                                        string="Journal Entries")

    paid_amount = fields.Monetary(compute='_compute_amount')
    remaining_amount = fields.Monetary(compute='_compute_amount')

    paid_interest = fields.Monetary(compute='_compute_amount')
    paid_penalty_interest = fields.Monetary(compute='_compute_amount')
    paid_principal = fields.Monetary(compute='_compute_amount')
    paid_fee = fields.Monetary(compute='_compute_amount')

    remaining_interest = fields.Monetary(compute='_compute_amount')
    remaining_penalty_interest = fields.Monetary(compute='_compute_amount')
    remaining_principal = fields.Monetary(compute='_compute_amount')
    remaining_fee = fields.Monetary(compute='_compute_amount')
    is_grace_installment = fields.Boolean(default=False)
    is_prepayment_line = fields.Boolean()
    status = fields.Selection([
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('unpaid', 'Unpaid')
    ], default='unpaid', compute='_compute_status', store=True)

    @api.depends('journal_entry_ids', 'journal_entry_ids', 'journal_entry_ids.state')
    def _compute_amount(self):
        """
        Method to compute paid amount
        """
        for rec in self:
            paid_interest = 0.0
            paid_penalty = 0.0
            paid_fee = 0.0
            paid_principal = 0.0

            total_paid_amount = 0.0

            for journal in rec.journal_entry_ids:
                if journal.state == 'posted':
                    total_paid_amount += journal.amount_total
                    paid_interest += sum(
                        journal.line_ids.filtered(lambda line: line.is_interest).mapped('credit'))
                    paid_penalty += sum(
                        journal.line_ids.filtered(lambda line: line.is_overdue_interest).mapped(
                            'credit'))
                    paid_fee += sum(
                        journal.line_ids.filtered(lambda line: line.is_fee).mapped('credit'))
                    paid_principal += sum(
                        journal.line_ids.filtered(lambda line: line.is_principal).mapped('credit'))

            rec.paid_amount = total_paid_amount
            rec.paid_interest = paid_interest
            rec.paid_penalty_interest = paid_penalty
            rec.paid_principal = paid_principal
            rec.paid_fee = paid_fee
            rec.remaining_amount = rec.total_installment_amount - total_paid_amount

            rec.remaining_interest = rec.interest_amount - paid_interest
            rec.remaining_penalty_interest = rec.penalty_interest - paid_penalty
            rec.remaining_principal = rec.installment_amount - paid_principal
            rec.remaining_fee = rec.fee_amount - paid_fee

    @api.depends('remaining_amount', 'total_installment_amount')
    def _compute_status(self):
        """
        Method to compute status
        """
        for rec in self:
            status = 'unpaid'
            total_installment_amount = rec.total_installment_amount
            remaining_amount = rec.remaining_amount

            if remaining_amount == 0:
                status = 'paid'
            elif remaining_amount < total_installment_amount:
                status = 'partial'
            rec.status = status

    def action_view_journals(self):
        """
        Method to view payment journal
        """
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'name': 'Journals',
            'res_model': 'account.move',
            'domain': [('move_type', '=', 'entry'), ('loan_line_id', '=', self.id)],
            'context': {
                'create': False
            }
        }

    @api.depends('customer_loan_id', 'emi_date', 'penalty_journal_entry_id',
                 'penalty_journal_entry_id.state')
    def _compute_set_od_count(self):
        for rec in self:
            rec.set_od_count = "set od count"
            loan_installments = self.env['customer.loan.lines'].search(
                [('customer_loan_id', '=', rec.customer_loan_id.id),
                 ('journal_entry_id', '!=', False),
                 ('emi_date', '<', rec.emi_date)],
                order="emi_date ASC")
            if (rec.penalty_journal_entry_id and rec.penalty_journal_entry_id.state == 'posted'
                    and not rec.is_count_set):
                rec.installment_od_count -= 1
                for installment in loan_installments:
                    installment.installment_od_count -= 1
                rec.is_count_set = True

    @api.depends('emi_date')
    def _compute_overdue_days(self):
        """
        Method to compute overdue days
        """
        for rec in self:
            if rec.display_type == 'line_section':
                rec.overdue_days = 0
                continue
            overdue_days = 0
            loan_id = rec.customer_loan_id
            if loan_id and loan_id.is_overdue_penalty_interest and loan_id.od_penalty_interest:
                today_date = datetime.date.today()
                emi_date = rec.emi_date

                if today_date > emi_date:
                    overdue_days = (today_date - emi_date).days
            rec.overdue_days = overdue_days

    @api.depends('invoice_id', 'invoice_id.amount_residual')
    def _compute_invoice_paid_date(self):
        """Compute invoice paid date"""
        for rec in self:
            invoice_date = False

            if rec.invoice_id and rec.invoice_id.payment_state in [
                'paid', 'in_payment']:
                payment_list = []
                payments = self.env['account.payment'].search([])
                for record in payments:
                    if rec.invoice_id.id in record.reconciled_invoice_ids.ids:
                        payment_list.append(record.date)

                if payment_list:
                    invoice_date = max(payment_list)

            rec.invoice_paid_date = invoice_date

    def action_create_journal_entry(self):
        """ Action create invoice """
        for rec in self:
            loan = rec.customer_loan_id

            if not rec.journal_entry_id and loan:
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
                if not loan.interest_income_account_id:
                    return display_message(
                        _("Interest Income Account Missing"),
                        _("To create journal entry, select interest income account in loan account details."))

                journal_lines = [(0, 0, {
                    'partner_id': loan.env.company.partner_id.id,
                    'account_id': loan.bank_cash_account.id,
                    'debit': rec.total_installment_amount
                }), (0, 0, {
                    'partner_id': loan.customer_id.id,
                    'account_id': loan.receivable_account_id.id,
                    'credit': rec.installment_amount
                }), (0, 0, {
                    'partner_id': loan.customer_id.id,
                    'account_id': loan.interest_income_account_id.id,
                    'credit': rec.total_installment_amount - rec.installment_amount
                })]

                journal_entry_id = self.env['account.move'].create({
                    'journal_id': loan.repayment_journal_item_id.id,
                    'ref': rec.installments_no,
                    'move_type': 'entry',
                    'customer_loan_id': loan.id,
                    'line_ids': journal_lines
                })
                rec.journal_entry_id = journal_entry_id.id


class CustomerLoanDocuments(models.Model):
    """Customer Loan documents"""
    _name = 'customer.loan.document.lines'
    _description = __doc__
    _rec_name = 'document_type_id'

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")
    document_type_id = fields.Many2one(comodel_name="customer.document.type", ondelete='restrict',
                                       required=True)
    document = fields.Binary()

    file_name = fields.Char()
    status = fields.Selection(
        selection=[('draft', 'Draft'), ('dept_verified', 'Department Verified'),
                   ('verified', 'Verified'),
                   ('rejected', 'Rejected'), ('cancelled', 'Cancelled')],
        default="draft")
    reason = fields.Char()
    validator_id = fields.Many2one(
        comodel_name="res.users", string="Validated By")
    is_department_verified = fields.Boolean(default=False)

    is_requested_from_customer = fields.Boolean(default=False)
    is_cancelled_by_customer = fields.Boolean(default=False)
    uploaded_status = (
        fields.Selection(selection=[('pending', 'Pending'), ('uploaded', 'Uploaded')],
                         compute="_compute_uploaded_status"))

    access_token = fields.Char()

    @api.depends('document')
    def _compute_uploaded_status(self):
        """compute uploaded status"""
        for rec in self:
            rec.uploaded_status = 'uploaded' if rec.document else 'pending'

    @api.ondelete(at_uninstall=False)
    def _ondelete_record(self):
        """ondelete record"""
        for rec in self:
            if rec.status != 'draft':
                raise ValidationError(
                    _('You can only delete records that are currently in the "Draft" stage.'
                      '\nPlease ensure the record you are attempting to delete is in the '
                      'Draft stage before proceeding.'))

    @api.constrains('document_type_id')
    def _check_document_type_id(self):
        """check document type"""
        for rec in self:
            doc_types = self.search(
                [('customer_loan_id', '=', rec.customer_loan_id.id), ('id', '!=', rec.id)])
            for doc_type in doc_types:
                if rec.document_type_id.id == doc_type.document_type_id.id:
                    raise ValidationError(
                        _(f"The {rec.document_type_id.name} is already added."))

    @api.model_create_multi
    def create(self, vals_list):
        """Create method"""
        res = super().create(vals_list)
        for rec in res:
            rec.access_token = secrets.token_urlsafe(16)
        return res

    def action_approve(self):
        """Approve the document"""
        for rec in self:
            if not rec.document:
                return display_message(
                    _("Invalid field document."),
                    _("Please upload the document before approving it.")
                )

            for req_doc in rec.customer_loan_id.req_document_ids:
                if rec.id in req_doc.cst_doc_lines_ids.ids and req_doc.stage == 'pending':
                    raise ValidationError(_(
                        f'{rec.document_type_id.name} has not been submitted by the customer.'
                        f'\nYou can approve the "{rec.document_type_id.name}" once it has been '
                        f'submitted by the customer.'))

            user = self.env.user
            is_dept_manager = user.has_group(
                'tk_loan_management.department_manager')

            body = Markup(f'<strong>Document : </strong>{rec.document_type_id.name}<br/>'
                          f'<strong>Approved By : </strong>{self.env.user.name}<br/>')

            if is_dept_manager:
                rec.status, rec.is_department_verified = 'verified', True
                post_message(self, body, None, None, 'doc')
            else:
                raise ValidationError(
                    _("You're not allowed to approve this document."))

            rec.validator_id = user.id

    def action_resubmit(self):
        """action resubmit"""
        for rec in self:
            rec.status = 'draft'
            rec.reason = ""
            rec.document = False


class CustomerCollateralLines(models.Model):
    """Customer Collateral Lines"""
    _name = 'customer.collateral.lines'
    _description = __doc__
    _rec_name = 'collateral_type_id'

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")
    collateral_type_id = fields.Many2one(comodel_name="customer.collateral.type",
                                         ondelete='restrict',
                                         required=True)
    document = fields.Binary()
    file_name = fields.Char()
    description = fields.Text()

    customer_note = fields.Text()

    is_requested_from_customer = fields.Boolean(default=False)
    uploaded_status = (
        fields.Selection(selection=[('pending', 'Pending'), ('uploaded', 'Uploaded')],
                         compute="_compute_uploaded_status"))
    access_token = fields.Char()
    is_cancelled_by_customer = fields.Boolean(default=False)

    status = fields.Selection(selection=[
        ('pending', 'Pending'), ('requested',
                                 'Requested'), ('submitted', 'Submitted'),
        ('rejected', 'Rejected')], default="pending")

    @api.model_create_multi
    def create(self, vals_list):
        """Create method"""
        res = super().create(vals_list)
        for rec in res:
            rec.access_token = secrets.token_urlsafe(16)
        return res

    @api.depends('document')
    def _compute_uploaded_status(self):
        """compute uploaded status"""
        for rec in self:
            rec.uploaded_status = 'uploaded' if rec.document else 'pending'


class InstallmentPenaltyLines(models.Model):
    """Installment's penalty lines"""
    _name = 'customer.loan.installment.penalty.lines'
    _description = __doc__
    _rec_name = 'customer_loan_id'

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")
    company_id = fields.Many2one(
        related='customer_loan_id.company_id', string='Company')
    currency_id = fields.Many2one(
        related='customer_loan_id.currency_id', string='Currency')
    penalty = fields.Char()
    installment_amount = fields.Monetary(currency_field="currency_id")
    penalty_amount = fields.Monetary(currency_field="currency_id")
    invoice_id = fields.Many2one(comodel_name="account.move")
    invoice_paid_date = fields.Date(compute="_compute_invoice_paid_date")
    invoice_state = fields.Selection(related="invoice_id.state")
    journal_entry_id = fields.Many2one('account.move')

    @api.depends('invoice_id', 'invoice_id.amount_residual')
    def _compute_invoice_paid_date(self):
        """Compute invoice paid date"""
        for rec in self:
            invoice_date = False

            if rec.invoice_id and rec.invoice_id.payment_state in [
                'paid', 'in_payment']:
                payment_list = []
                payments = self.env['account.payment'].search([])
                for record in payments:
                    if rec.invoice_id.id in record.reconciled_invoice_ids.ids:
                        payment_list.append(record.date)
                if payment_list:
                    invoice_date = max(payment_list)
            rec.invoice_paid_date = invoice_date


class CustomerLoanRequestedDocument(models.Model):
    """Customer Loan Request Document"""
    _name = 'customer.loan.request.document'
    _description = __doc__

    customer_loan_id = fields.Many2one(comodel_name="customer.loan", ondelete="cascade")
    name = fields.Char()
    cst_doc_lines_ids = (
        fields.Many2many(
            comodel_name="customer.loan.document.lines", relation="cst_req_doc_rel",
            column1="cst_req_doc_id", column2="cstl_doc_id", string="Requested Documents"))
    stage = fields.Selection(
        selection=[('submitted', 'Submitted'), ('pending', 'pending'), ('rejected', 'Rejected')])
    access_token = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        """Create method"""
        res = super().create(vals_list)
        for rec in res:
            rec.name = self.env['ir.sequence'].next_by_code(
                'customer.loan.req.doc.sequence') or 'New'
            rec.access_token = secrets.token_urlsafe(16)
        return res


class CustomerLoanRequestedCollateral(models.Model):
    """Customer Loan Request Document"""
    _name = 'customer.loan.request.collateral'
    _description = __doc__

    customer_loan_id = fields.Many2one(comodel_name="customer.loan")
    name = fields.Char()
    cst_collateral_doc_lines_ids = (
        fields.Many2many(
            comodel_name="customer.collateral.lines", relation="cst_req_col_doc_rel",
            column1="cst_req_col_doc_id", column2="cstl_col_doc_id", string="Requested Documents"))

    req_collateral_ids = fields.Many2many(
        comodel_name="customer.collateral.type", relation="req_col_rel", column1="req_col_id",
        column2="col_type_id", string="Requested Collateral")

    stage = fields.Selection(
        selection=[('submitted', 'Submitted'), ('pending',
                                                'pending'), ('rejected', 'Rejected')],
        default='pending')
    access_token = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        """Create method"""
        res = super().create(vals_list)
        for rec in res:
            rec.name = self.env['ir.sequence'].next_by_code(
                'customer.loan.req.col.doc.sequence') or 'New'
            rec.access_token = secrets.token_urlsafe(16)
        return res


class CustomerLoanSanctionLatter(models.Model):
    """
    Model to manage the customer sanction latters along with
    rejection reasons
    """
    _name = 'customer.loan.sanction.latter'
    _description = __doc__

    access_token = fields.Char()
    name = fields.Char(string="Latter No.", default='New')
    cst_conf_stage = fields.Selection(
        selection=[('draft', 'Draft'), ('sent', 'Sent'), ('signed', 'Signed'),
                   ('expired', 'Expired'),
                   ('rejected', 'Rejected'),
                   ('cancelled', 'Cancelled')], default='draft', string="Status")
    cst_response_stage = fields.Selection(
        selection=[('draft', 'Draft'), ('reject_reopen', 'Reject Reopen'),
                   ('reopen_expired', 'Reopen Expired')],
        default='draft')
    sent_date_time = fields.Datetime()
    accept_date_time = fields.Datetime()
    expiry_date = fields.Date(compute="_compute_expiry_date", store=True)
    is_expired = fields.Boolean(default=False)
    cst_sign = fields.Image()
    sign_by = fields.Char()
    signature_hash = fields.Char()
    event_hash = fields.Char()
    cst_loan_reject_reason = fields.Text()
    loan_id = fields.Many2one('customer.loan')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create method to add access token
        while creating new record
        """
        res = super(CustomerLoanSanctionLatter, self).create(vals_list)
        for rec in res:
            rec.access_token = secrets.token_urlsafe(12)
            active_sanction_latters = self.search([
                ('id', '!=', rec.id),
                ('cst_conf_stage', '=', 'sent')
            ])
            rec.name = self.env['ir.sequence'].next_by_code(
                'customer.loan.sanction.letter.sequence') or 'New'
            if active_sanction_latters:
                active_sanction_latters.write({
                    "cst_conf_stage": 'expired'
                })
        return res

    @api.depends('sent_date_time')
    def _compute_expiry_date(self):
        """compute expiry date"""
        for rec in self:
            expiry_date = False
            if rec.sent_date_time:
                sanction_letter_expire_days = self.env['ir.config_parameter'].sudo().get_param(
                    'tk_loan_management.sanction_letter_expire_days')
                if not sanction_letter_expire_days:
                    expiry_date = rec.sent_date_time + timedelta(days=3)
                else:
                    expiry_date = rec.sent_date_time + timedelta(
                        days=int(sanction_letter_expire_days))
            rec.expiry_date = expiry_date

    def _compute_loan_hash(self, data):
        """Utility function to compute SHA-256 hash."""
        return sha256(data.encode('utf-8')).hexdigest()

    def get_signature_hash(self):
        """Generate signature and event hashes."""
        self.signature_hash = self._compute_loan_hash(str(self.cst_sign))
        self.event_hash = self._compute_loan_hash(self._prepare_event_hash())

    def _prepare_event_hash(self):
        """Prepare and serialize the event data for hashing."""
        event_data = {
            'sent_datetime': str(self.sent_date_time),
            'accept_date_time': str(self.accept_date_time),
            'loan_amount': str(self.loan_id.loan_amount),
            'interest_rate': str(self.loan_id.interest_rate),
            'installment_type': str(self.loan_id.installment_type),
            'customer_name': str(self.loan_id.customer_id.name),
            'cst_conf_stage': 'signed',
            'loan_lines_ids': str(self.loan_id.loan_lines_ids.read()),
            'terms_and_conditions': str(self.loan_id.terms_and_conditions),
            'repayment_terms': str(self.loan_id.repayment_terms)
        }
        # Sorted keys and UTF-8 encoding
        return json.dumps(event_data, sort_keys=True, ensure_ascii=False)

    def sign_loan_application(self, sign, sign_by):
        """sign loan application"""
        self.write({
            'cst_sign': sign,
            'sign_by': sign_by,
            'accept_date_time': fields.Datetime.now(),
            'cst_conf_stage': 'signed',
        })
