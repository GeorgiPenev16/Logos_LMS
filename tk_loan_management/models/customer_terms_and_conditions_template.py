# -*- coding: utf-8 -*-
# Copyright 2024 - Today Techkhedut.
# Part of Techkhedut. See LICENSE file for full copyright and licensing detail
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CustomerTermsAndConditionsTemplate(models.Model):
    """Customer Terms & Conditions Template"""
    _name = 'customer.terms.and.conditions.template'
    _description = __doc__

    name = fields.Char(required=True)
    terms_and_conditions = fields.Html()

    @api.constrains('name')
    def _check_terms_and_condition_template(self):
        """check terms and conditions template"""
        for rec in self:
            terms = self.search([('id', '!=', rec.id), ('name', '=', rec.name)])
            for term in terms:
                if term.name == rec.name:
                    raise ValidationError(
                        _(f"{rec.name} has already been added in the terms and conditions "
                        f"templates.\nPlease add the terms and conditions template under a " 
                        f"different name."))

    def copy(self, default=None):
        """copy method"""
        if default is None:
            default = {}
        # Set default name for the copied record
        if not default.get('name'):
            default['name'] = _('%s(Copy)', self.name)

        return super().copy(default)
