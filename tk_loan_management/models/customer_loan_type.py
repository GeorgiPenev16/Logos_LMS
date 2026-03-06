# -*- coding: utf-8 -*-
# Copyright 2024 - Today Techkhedut.
# Part of Techkhedut. See LICENSE file for full copyright and licensing detail
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CustomerLoanType(models.Model):
    """Customer Loan Type"""
    _name = 'customer.loan.type'
    _inherits = {"product.product": "product_id"}
    _description = __doc__

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='company_id.currency_id', string='Currency')
    product_id = fields.Many2one(comodel_name="product.product", required=True, ondelete="cascade",
                                 index=True, readonly=False, string="Related Product",
                                 help="Related Product of product.product")
    type = fields.Selection(related="product_id.type", default='service', inherited=True,
                            readonly=False)
    is_interest = fields.Boolean(string="Apply Interest")
    interest_rate = fields.Float()

    terms_and_conditions_template_id = fields.Many2one(
        comodel_name="customer.terms.and.conditions.template")
    terms_and_conditions = fields.Html()

    repayment_terms_template_id = fields.Many2one(comodel_name="customer.repayment.terms.template")
    repayment_terms = fields.Html()

    term_template_id = fields.Many2one(comodel_name="customer.term.template")

    term_lines_ids = fields.One2many(comodel_name="customer.loan.type.term.lines",
                                     inverse_name="loan_type_id")
    loan_doc_ids = fields.One2many(comodel_name="loan.type.document.lines",
                                   inverse_name="loan_type_id")

    # Fees details
    is_fee = fields.Boolean()
    fee_amount = fields.Float(string="Fee")
    is_initial_fee = fields.Boolean()
    initial_fee_amount = fields.Float(string="Initial Fee")

    # Overdue penalty interest
    is_overdue_penalty_interest = fields.Boolean(string='Apply overdue interest')
    od_penalty_interest = fields.Float(string="Overdue Interest")

    @api.constrains('is_fee', 'fee_amount')
    def _validate_fee_amount(self):
        """
        Method to check that if there installment fee than
        """
        for rec in self:
            if rec.is_fee and rec.fee_amount <= 0:
                raise ValidationError(_("The value for fee amount should not be zero and less."))

    @api.depends('is_overdue_penalty_interest', 'od_penalty_interest')
    def _check_overdue_penalty_interest(self):
        for rec in self:
            if rec.is_overdue_penalty_interest and rec.od_penalty_interest <= 0.0:
                raise ValidationError(_("Overdue penalty interest can't be zero or less."))

    @api.onchange('is_overdue_penalty_interest')
    def _onchange_overdue_penalty_interest(self):
        """
        Method to reset overdue penalty interest
        when overdue penalty not available
        """
        for rec in self:
            if not rec.is_overdue_penalty_interest:
                rec.od_penalty_interest = 0.0

    @api.onchange('is_initial_fee')
    def _onchange_initial_fee(self):
        """
        Method to remove initial fee amount if is_initial_fee is not True
        """
        for rec in self:
            rec.initial_fee_amount = 0.0

    @api.onchange('is_initial_fee')
    def _onchange_initial_fee(self):
        """
        Method to remove initial fee amount if is_initial_fee is not True
        """
        for rec in self:
            rec.initial_fee_amount = 0.0

    @api.onchange('term_template_id')
    def _onchange_term_template_id(self):
        """onchange term template id"""
        for rec in self:
            rec.term_lines_ids = [(5, 0, 0)]
            for term_lines in rec.term_template_id.template_line_ids:
                rec.term_lines_ids = [(0, 0, {'loan_type_id': rec.id,
                                              'duration': term_lines.duration,
                                              'interest_rate': term_lines.interest_rate,
                                              'installment_type': term_lines.installment_type,
                                              })]

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


class CustomerLoanTypeTermLines(models.Model):
    """Customer Loan Type Term Lines"""
    _name = 'customer.loan.type.term.lines'
    _description = __doc__

    loan_type_id = fields.Many2one(comodel_name="customer.loan.type")
    duration = fields.Integer(string="Upto (Installments)")
    interest_rate = fields.Float()

    installment_type = fields.Selection(
        selection=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')],
        default="monthly", required=True)

    @api.constrains('duration', 'installment_type')
    def _check_duration(self):
        """check duration"""
        for rec in self:
            term_lines = self.search(
                [('id', '!=', rec.id), ('loan_type_id', '=', rec.loan_type_id.id)])
            for term in term_lines:
                if term.duration == rec.duration and term.installment_type == rec.installment_type:
                    raise ValidationError(
                        _(f"Upto {rec.duration} {rec.installment_type} installments term is "
                          f"already added."))

    @api.constrains('interest_rate')
    def _check_interest_rate(self):
        """check interest rate"""
        for rec in self:
            if rec.interest_rate < 0:
                raise ValidationError(
                    _(f'The interest rate cannot be a negative number.\nPlease enter a valid '
                      f'positive value in Upto {rec.duration} {rec.installment_type} '
                      f'Installments.'))


class LoanTypeDocumentLines(models.Model):
    """Loan Type Documents"""
    _name = 'loan.type.document.lines'
    _description = __doc__

    loan_type_id = fields.Many2one(comodel_name="customer.loan.type")
    document_type_id = fields.Many2one(comodel_name="customer.document.type", ondelete='restrict')

    @api.constrains('document_type_id')
    def _check_document_type_id(self):
        """check document"""
        for rec in self:
            documents = self.search(
                [('id', '!=', rec.id), ('loan_type_id', '=', rec.loan_type_id.id)])
            for doc in documents:
                if doc.document_type_id.id == rec.document_type_id.id:
                    raise ValidationError(
                        _(f"In Documents {rec.document_type_id.name} has already been added."))
