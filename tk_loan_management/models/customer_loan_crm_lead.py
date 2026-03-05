# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from html.parser import HTMLParser
from odoo import fields, api, models, _


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


class MyHTMLParser(HTMLParser):
    """My html parser"""

    def __init__(self):
        super().__init__()
        self.text = ''

    def handle_starttag(self, tag, attrs):
        """handle start tag"""
        # Add newline before certain tags
        if tag in ['br', 'p', 'h1', 'h2', 'h3', 'h4', 'tr', 'th', 'div']:
            self.text += '\n'
        elif tag == 'li':
            self.text += '\n- '
        elif tag == 'span':
            self.text += ' '

    def handle_data(self, data):
        """handle data"""
        # Append the text content
        self.text += data.strip()

    def handle_endtag(self, tag):
        """handle end tag"""
        # Add newline after certain tags
        if tag in ['br', 'p', 'h1', 'h2', 'h3', 'h4', 'tr', 'th', 'div']:
            self.text += '\n'


def parse_html(html):
    """parse html"""
    parser = MyHTMLParser()
    parser.feed(html)
    return parser.text


class CustomerLoanCrmLead(models.Model):
    """Customer Loan Crm lead"""
    _inherit = 'crm.lead'
    _description = __doc__

    currency_id = fields.Many2one(
        comodel_name='res.currency', related='company_id.currency_id', string='Loan Currency')

    access_token = fields.Char()

    app_date = fields.Date(string="Application Date", default=fields.Date.today(), tracking=True)
    requested_start_date = (
        fields.Date(default=fields.Date.today(), string="Expected Start Date", tracking=True))

    # requested loan details
    approved_loan_type_id = (
        fields.Many2one(comodel_name="customer.loan.type", string="Loan Type"))
    requested_loan_amount = (
        fields.Monetary(currency_field="currency_id", string="Loan Amount"))
    requested_term = fields.Integer(string="Term")
    requested_installment_type = fields.Selection(
        selection=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')],
        default="monthly")

    # Disbursement
    disbursement_payment_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer')
    ])

    # customer bank details
    cst_bank_name = fields.Char(string="Bank Name", tracking=True)
    cst_bank_account_number = fields.Char(string="Account Number", tracking=True)
    cst_bank_branch_name = fields.Char(string="Branch Name", tracking=True)
    cst_bank_branch_code = fields.Char(string="Branch Code", tracking=True)
    cst_bank_swift_bic_code = fields.Char(string="SWIFT/BIC Code", tracking=True)

    customer_loan_id = fields.Many2one(comodel_name='customer.loan')
    crm_customer_doc_ids = fields.One2many(comodel_name="crm.customer.loan.document.lines",
                                           inverse_name='crm_customer_loan_id')
    # Terms and conditions
    terms_and_conditions_template_id = fields.Many2one(
        comodel_name="customer.terms.and.conditions.template", tracking=True)
    terms_and_conditions = fields.Html()

    # Repayment terms
    repayment_terms_template_id = (
        fields.Many2one(comodel_name="customer.repayment.terms.template", tracking=True))
    repayment_terms = fields.Html()

    loan_req_status = fields.Selection(
        selection=[('in_progress', 'In Progress'), ('approved', 'Approved'),
                   ('cancelled', 'Cancelled')])

    customer_requested_loan_tracking_url = fields.Char()

    stage_id_name = fields.Char(related="stage_id.name")
    is_in_won_stage = fields.Boolean(related="stage_id.is_won")

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer')
    ])

    # Employer details
    ep_zip = fields.Char(string='Zip ')
    ep_street = fields.Char(string='Street1 ', translate=True)
    ep_street2 = fields.Char(string='Street2 ', translate=True)
    ep_city = fields.Char(string='City ', translate=True)
    ep_country_id = fields.Many2one('res.country', 'Country ')
    ep_state_id = fields.Many2one(
        "res.country.state", string='State ', store=True,
        domain="[('country_id', '=?', country_id)]")

    def action_show_customer_loan(self):
        """Action show customer"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Loan',
            'res_model': 'customer.loan',
            'res_id': self.customer_loan_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False},
        }

    @api.onchange('terms_and_conditions_template_id')
    def _onchange_terms_and_conditions_template_id(self):
        """onchange terms and condition template id"""
        for rec in self:
            rec.terms_and_conditions = rec.terms_and_conditions_template_id.terms_and_conditions

    @api.onchange('repayment_terms_template_id')
    def _onchange_repayment_terms_template_id(self):
        """onchange repayment terms template id"""
        for rec in self:
            rec.repayment_terms = rec.repayment_terms_template_id.repayment_terms

    @api.onchange('approved_loan_type_id')
    def _onchange_loan_type_id(self):
        """
        On change loan type id 
        """
        for rec in self:
            rec.crm_customer_doc_ids = [(5, 0, 0)]
            loan_type_id = rec.approved_loan_type_id
            document_ids = []

            if loan_type_id:
                documents = loan_type_id.loan_doc_ids

                for doc in documents:
                    document_ids.append((0, 0, {
                        "document_type_id": doc.document_type_id.id
                    }))
            rec.write({
                "crm_customer_doc_ids": document_ids
            })

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Method to get partner details
        on changing the partner
        """
        for rec in self:
            account_number = None
            payment_method = None
            ep_street = None
            ep_street2 = None
            ep_city = None
            ep_state_id = None
            ep_country_id = None
            ep_zip = None

            partner_id = rec.partner_id

            if partner_id:
                account_number = partner_id.bank_account
                payment_method = partner_id.payment_method
                ep_street = partner_id.ep_street
                ep_street2 = partner_id.ep_street2
                ep_city = partner_id.ep_city
                ep_state_id = partner_id.ep_state_id.id
                ep_country_id = partner_id.ep_country_id.id
                ep_zip = partner_id.ep_zip

            rec.cst_bank_account_number = account_number
            rec.payment_method = payment_method
            rec.ep_street = ep_street
            rec.ep_street2 = ep_street2
            rec.ep_city = ep_city
            rec.ep_state_id = ep_state_id
            rec.ep_country_id = ep_country_id
            rec.ep_zip = ep_zip

    @api.onchange('ep_country_id')
    def _onchange_country_id(self):
        """On change country ID"""
        if self.ep_country_id and self.ep_country_id != self.ep_state_id.country_id:
            self.ep_state_id = False

    @api.onchange('ep_state_id')
    def _onchange_state(self):
        """On Change state"""
        if self.ep_state_id.country_id:
            self.ep_country_id = self.ep_state_id.country_id

    def action_set_won_rainbowman(self):
        """action set won rainbowman"""
        res = super().action_set_won_rainbowman()
        self.loan_req_status = 'approved'
        return res

    def toggle_active(self):
        """toggle active"""
        res = super().toggle_active()
        self.loan_req_status = 'in_progress'"Please select customer."
        return res

    def action_create_customer_loan(self):
        """Action create customer loan"""
        if not self.partner_id:
            return display_message(_("Invalid field"), _("Please select customer."))
        elif not self.email_from:
            return display_message(_("Invalid field"), _("Please add email."))
        elif not self.phone:
            return display_message(_("Invalid field"), _("Please add phone."))
        elif not self.app_date:
            return display_message(_("Invalid field"), _("Please select application date."))
        elif not self.requested_start_date:
            return display_message(_("Invalid field"), _("Please select requested start date."))
        elif not self.approved_loan_type_id:
            return display_message(_("Invalid field"), _("Please select loan type."))
        elif not self.cst_bank_name:
            return display_message(_("Invalid field"), _("Please add bank name."))
        elif not self.cst_bank_account_number:
            return display_message(_("Invalid field"), _("Please add bank account number."))
        elif not self.cst_bank_branch_code:
            return display_message(_("Invalid field"), _("Please add branch code"))
        elif not self.cst_bank_swift_bic_code:
            return display_message(_("Invalid field"), _("Please add SWIFT/BIC code."))
        elif not self.crm_customer_doc_ids:
            return display_message(_("Invalid field"), _("Please add documents."))
        elif self.loan_req_status != 'approved':
            return display_message(
                _("Not approved!"),
                _("Please approve the loan request before creating the customer loan."))

        loan_details = {
            'customer_id': self.partner_id.id,
            'responsible_id': self.user_id.id if self.user_id else self.env.user.id,
            'lead_id': self.id,
            'app_date': self.app_date,
            'requested_start_date': self.requested_start_date,
            'start_date': self.requested_start_date,
            'installment_start_date': self.requested_start_date,
            'approved_loan_type_id': self.approved_loan_type_id.id,
            'requested_loan_amount': self.requested_loan_amount,
            'requested_term': self.requested_term,
            'term': self.requested_term,
            'requested_installment_type': self.requested_installment_type,
            'cst_bank_name': self.cst_bank_name,
            'cst_bank_account_number': self.cst_bank_account_number,
            'cst_bank_branch_name': self.cst_bank_branch_name,
            'cst_bank_branch_code': self.cst_bank_branch_code,
            'cst_bank_swift_bic_code': self.cst_bank_swift_bic_code,
            'customer_loan_doc_ids': [(0, 0, {'document_type_id': doc.document_type_id.id,
                                              'document': doc.document if doc.document else False,
                                              'file_name': doc.file_name if doc.file_name else False
                                              }) for doc in
                                      self.crm_customer_doc_ids],
            'terms_and_conditions_template_id': self.terms_and_conditions_template_id.id,
            'repayment_terms_template_id': self.repayment_terms_template_id.id,
            'terms_and_conditions': self.terms_and_conditions,
            'repayment_terms': self.repayment_terms,
            'loan_purpose': parse_html(self.description) if self.description else None,
            'disbursement_payment_type': self.disbursement_payment_type
        }

        customer_loan = self.env['customer.loan'].create(loan_details)
        self.customer_loan_id = customer_loan.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Loan',
            'res_model': 'customer.loan',
            'res_id': customer_loan.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False},
        }

    def action_update_customer_details(self):
        """
        Method to update customer details
        """
        customer_id = self.partner_id
        if customer_id:
            customer_id.write({
                "bank_account": self.cst_bank_account_number,
                "payment_method": self.payment_method,
                "ep_street": self.ep_street,
                "ep_street2": self.ep_street2,
                "ep_city": self.ep_city,
                "ep_state_id": self.ep_state_id.id,
                "ep_country_id": self.ep_country_id,
                "ep_zip": self.ep_zip
            })


class CRMCustomerLoanDocuments(models.Model):
    """CRM Customer Loan documents"""
    _name = 'crm.customer.loan.document.lines'
    _description = __doc__
    _rec_name = 'document_type_id'

    crm_customer_loan_id = fields.Many2one(comodel_name="crm.lead")
    document_type_id = fields.Many2one(comodel_name="customer.document.type", ondelete='restrict',
                                       required=True)
    document = fields.Binary(required=True)
    file_name = fields.Char()


class CrmCustomerLoanLeadLost(models.TransientModel):
    """Get Lost Reason"""
    _inherit = 'crm.lead.lost'
    _description = __doc__

    @api.model
    def default_get(self, fields):
        """Default get"""
        record = super().default_get(fields)
        customer_req_loan = self.env['crm.lead'].browse(
            self.env.context.get('active_id'))
        record['customer_req_loan_id'] = customer_req_loan.id
        return record

    customer_req_loan_id = fields.Many2one(comodel_name="crm.lead")

    def action_lost_reason_apply(self):
        """action lost reason apply"""
        res = super().action_lost_reason_apply()
        self.customer_req_loan_id.loan_req_status = 'cancelled'
        return res
