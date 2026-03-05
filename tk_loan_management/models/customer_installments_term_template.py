# -*- coding: utf-8 -*-
# Copyright 2024 - Today Techkhedut.
# Part of Techkhedut. See LICENSE file for full copyright and licensing detail
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CustomerInstallmentTermTemplate(models.Model):
    """Customer Installments Term Template"""
    _name = 'customer.term.template'
    _description = __doc__

    name = fields.Char(required=True)
    template_line_ids = fields.One2many(comodel_name="customer.term.template.lines",
                                        inverse_name="term_template_id")

    @api.constrains('name')
    def _check_term(self):
        """check term"""
        for rec in self:
            terms = self.search([('id', '!=', rec.id), ('name', '=', rec.name)])
            for term in terms:
                if term.name == rec.name:
                    raise ValidationError(
                        _(f"{rec.name} has already been added in the installment term templates."
                          f"\nPlease add the installments term template under a different name."))

    def copy(self, default=None):
        """copy method"""
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _('%s(Copy)', self.name)

        new_record = super().copy(default)

        if hasattr(self, 'template_line_ids'):
            for line in getattr(self, 'template_line_ids'):
                line.copy({
                    'term_template_id': new_record.id,
                })

        return new_record


class CustomerInstallmentTermTemplateLines(models.Model):
    """Customer Installments Term Template Lines"""
    _name = 'customer.term.template.lines'
    _description = __doc__

    term_template_id = fields.Many2one(comodel_name="customer.term.template")
    duration = fields.Integer(string="Upto (Installments)")
    interest_rate = fields.Float()
    installment_type = fields.Selection(
        selection=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')],
        default="monthly",
        required=True)

    @api.constrains('duration', 'installment_type')
    def _check_duration(self):
        """check duration"""
        for rec in self:
            term_lines = self.search(
                [('id', '!=', rec.id), ('term_template_id', '=', rec.term_template_id.id)])
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
                      f'positive value in Upto {rec.duration} '
                      f'{rec.installment_type} installments.'))
