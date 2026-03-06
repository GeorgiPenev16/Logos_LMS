# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CustomerLoanResConfigSettings(models.TransientModel):
    """Customer Loan res config settings"""
    _inherit = 'res.config.settings'

    sanction_letter_expire_days = (
        fields.Integer(config_parameter="tk_loan_management.sanction_letter_expire_days",
                       default=3))
    processing_fee_id = (
        fields.Many2one(comodel_name="product.product",
                        config_parameter='tk_loan_management.processing_fee_id'))
    processing_fee_status = (
        fields.Selection(selection=[('draft', 'Draft'), ('posted', 'Posted')],
                         default="posted",
                         config_parameter='tk_loan_management.processing_fee_status'))

    installment_id = fields.Many2one(comodel_name="product.product",
                                     config_parameter='tk_loan_management.installment_id')
    installment_reminder_days = (
        fields.Integer(config_parameter="tk_loan_management.installment_reminder_days",
                       default=10))

    penalty_id = fields.Many2one(comodel_name="product.product",
                                 config_parameter='tk_loan_management.penalty_id')

    pre_closure_charge_id = (
        fields.Many2one(comodel_name="product.product",
                        config_parameter='tk_loan_management.pre_closure_charge_id'))
    pre_closure_interest_id = (
        fields.Many2one(comodel_name="product.product",
                        config_parameter='tk_loan_management.pre_closure_interest_id'))
    pre_closure_installment_id = (
        fields.Many2one(comodel_name="product.product",
                        config_parameter='tk_loan_management.pre_closure_installment_id'))

    settlement_id = fields.Many2one(comodel_name="product.product",
                                    config_parameter='tk_loan_management.settlement_id')

    sales_person_id = fields.Many2one(comodel_name="res.users",
                                      config_parameter='tk_loan_management.sales_person_id')

    @api.constrains('sanction_letter_expire_days')
    def _check_sanction_letter_expire_days(self):
        """check sanction letter expire days"""
        for rec in self:
            if rec.sanction_letter_expire_days < 1:
                raise ValidationError(
                    _("Invalid input: The number of sanction letter expire days must be greater "
                      "than zero."))

    @api.constrains('installment_reminder_days')
    def _check_installment_reminder_days(self):
        """check installment reminder days"""
        for rec in self:
            if rec.installment_reminder_days < 1:
                raise ValidationError(
                    _("Invalid input: The number of installment reminder days must be greater "
                      "than zero."))
