# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from datetime import date
import re
from dateutil import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CustomerLoanResPartner(models.Model):
    """Customer Loan Res Partner"""
    _inherit = "res.partner"
    _description = __doc__

    # Customer document details
    is_document_uploaded = fields.Boolean(default=True)
    loan_to_review_for_doc_upload = fields.Integer()
    docs_upload_pending = fields.Integer()

    # Collateral details
    is_collateral_added = fields.Boolean(default=True)
    loan_to_review_for_collateral_upload = fields.Integer()
    collateral_upload_pending = fields.Integer()

    # Other info
    personal_number = fields.Char()
    id_card = fields.Char()
    validity_type = fields.Selection([
        ('10_years', '10 Years'),
        ('indefinite', 'Indefinite')
    ])
    date_of_issuing = fields.Date(string='Date of Issuing')
    date_of_validity = fields.Date(string='Date of Validity')
    issued_by = fields.Char()
    codebtor_ids = fields.Many2many('res.partner', 'loan_codebtor_rel_res_partner', 'codebtor',
                                    'partner_id', string="Codebtor ")

    # Family information
    family_info_id = fields.Many2one('family.info')
    no_of_children = fields.Integer(string='No. of Children')
    date_of_salary_to = fields.Selection([
        ('10', '10'),
        ('20', '20'),
        ('30', '30')
    ], string="Date of Salary To")

    is_loan_borrower = fields.Boolean(string='Loan Borrower')
    is_person_of_contact = fields.Boolean(string="Person of contact")
    is_codebtor = fields.Boolean(string="Codebtor")


    # Employer details
    labour_relation_id = fields.Many2one('labour.relation', string='Labour Relation')
    employer = fields.Char()
    ep_zip = fields.Char(string='Zip ')
    ep_street = fields.Char(string='Street1 ', translate=True)
    ep_street2 = fields.Char(string='Street2 ', translate=True)
    ep_city = fields.Char(string='City ', translate=True)
    ep_country_id = fields.Many2one('res.country', 'Country ')
    ep_state_id = fields.Many2one(
        "res.country.state", string='State ', store=True,
        domain="[('country_id', '=?', ep_country_id)]")

    # Income and expense details
    income_line_ids = fields.One2many('customer.income.line', 'customer_id')
    expense_line_ids = fields.One2many('customer.expense.line', 'customer_id')
    total_income = fields.Monetary(compute='_compute_total_income')
    total_expense = fields.Monetary(compute='_compute_total_expense')

    # Payment details
    bank_account = fields.Char(string='Bank Account')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer')
    ])

    # Notes
    notes = fields.Html(string='Notes ')

    @api.constrains('personal_number', 'id_card')
    def _check_personal_number(self):
        for rec in self:
            personal_number = rec.personal_number
            id_card = rec.id_card
            if personal_number:
                is_valid_personal_number, error_msg = self.is_valid_egn(personal_number)
                if not is_valid_personal_number:
                    raise ValidationError(_(f"{error_msg}"))
            if id_card and not self.is_valid_id_card(id_card):
                raise ValidationError(_("Invalid id card number."))

    @api.depends('income_line_ids', 'income_line_ids.amount')
    def _compute_total_income(self):
        """
        Method to compute the total income
        """
        for rec in self:
            rec.total_income = sum(rec.income_line_ids.mapped('amount'))

    @api.depends('expense_line_ids')
    def _compute_total_expense(self):
        """
        Method to compute total expense
        """
        for rec in self:
            rec.total_expense = sum(rec.expense_line_ids.mapped('amount'))

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

    @api.onchange('date_of_issuing', 'validity_type')
    def onchange_issuing_date(self):
        """
        This method will calculate the expiry date of the id card
        on changing the issuing date
        """
        for rec in self:
            issuing_date, validity_date, = rec.date_of_issuing, None
            if issuing_date and rec.validity_type == '10_years':
                validity_date = issuing_date + relativedelta.relativedelta(years=10)
            rec.date_of_validity = validity_date

    @staticmethod
    def is_valid_egn(egn: str):
        """
        Performs a full validation of a Bulgarian Personal Code (EGN).

        This function checks for:
        1.  Correct format (exactly 10 digits).
        2.  A valid birth date, accounting for centuries before 1900,
            the 20th century, and the 21st century.
        3.  A correct checksum based on the standard weighting algorithm.

        Args:
            egn (str): The EGN to validate, passed as a string.

        Returns:
            bool: True if the EGN is valid, False otherwise.
        """
        # 1. Check if the EGN consists of exactly 10 digits using regex.
        if not re.match(r'^\d{10}$', egn):
            return False, "Value for personal number should be the ten digits."

        # 2. Extract year, month, and day parts.
        try:
            year_part = int(egn[0:2])
            month_part = int(egn[2:4])
            day_part = int(egn[4:6])
        except ValueError:
            return False, "Value for personal number should be the ten digits number."  # Should not happen with the regex, but good practice.

        # 3. Determine the full year and month based on the month part.
        if 41 <= month_part <= 52:
            # Born in the 21st century (2000-2099)
            year = 2000 + year_part
            month = month_part - 40
        elif 21 <= month_part <= 32:
            # Born in the 19th century (1800-1899)
            year = 1800 + year_part
            month = month_part - 20
        elif 1 <= month_part <= 12:
            # Born in the 20th century (1900-1999)
            year = 1900 + year_part
            month = month_part
        else:
            # Invalid month part.
            return False, "Invalid month part from the personal number."

        # 4. Validate if the extracted date is a real calendar date.
        try:
            date(year, month, day_part)
        except ValueError:
            # The date is invalid (e.g., February 30th).
            return False, "Invalid date of birth inside personal number."

        # 5. Calculate and validate the checksum.
        weights = [2, 4, 8, 5, 10, 9, 7, 3, 6]
        checksum_sum = 0
        for i in range(9):
            checksum_sum += int(egn[i]) * weights[i]

        calculated_checksum = checksum_sum % 11
        if calculated_checksum == 10:
            calculated_checksum = 0

        # Compare calculated checksum with the last digit of the EGN.
        egn_checksum = int(egn[9])

        if egn_checksum == calculated_checksum:
            return True, None
        else:
            return False, "Invalid value for personal number."

    @staticmethod
    def is_valid_id_card(id_card: str) -> bool:
        """
        Validate an ID card string against two accepted formats:

        1. A 9-digit number (e.g., "123456789")
        2. Two uppercase letters followed by 7 digits (e.g., "AB1234567")
        :param id_card:
        :return: boolean
        """
        pattern_digits = r'^\d{9}$'  # 9-digit number
        pattern_alpha_num = r'^[A-Z]{2}\d{7}$'  # 2 uppercase letters followed by 7 digits

        return bool(re.match(pattern_digits, id_card) or
                    re.match(pattern_alpha_num, id_card))


class CustomerIncomeLine(models.Model):
    """Customer income lines"""
    _name = 'customer.income.line'
    _description = __doc__

    type = fields.Char()
    amount = fields.Monetary()
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id.id)
    customer_id = fields.Many2one('res.partner')


class CustomerExpenseLine(models.Model):
    """
    Customer expense line
    """
    _name = 'customer.expense.line'
    _description = __doc__

    type = fields.Char()
    company_name = fields.Char()
    amount = fields.Monetary()
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id.id)
    monthly_payment = fields.Monetary()
    customer_id = fields.Many2one('res.partner')


class CustomerFamilyInfo(models.Model):
    """Model to manage family info"""
    _name = 'family.info'
    _description = __doc__
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title')


class LabourRelation(models.Model):
    """Model to manage labour information"""
    _name = 'labour.relation'
    _description = __doc__
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Title")
