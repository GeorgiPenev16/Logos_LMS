# -*- coding: utf-8 -*-
# Copyright 2024 - Today Techkhedut.
# Part of Techkhedut. See LICENSE file for full copyright and licensing detail
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CustomerRepaymentTermsTemplate(models.Model):
    """Customer Repayment Terms Template"""
    _name = 'customer.repayment.terms.template'
    _description = __doc__

    name = fields.Char(required=True)
    repayment_terms = fields.Html()

    @api.constrains('name')
    def _check_repayment_terms_template(self):
        """check repayment terms template"""
        for rec in self:
            terms = self.search([('id', '!=', rec.id), ('name', '=', rec.name)])
            for term in terms:
                if term.name == rec.name:
                    raise ValidationError(_(f"{rec.name} has already been added in the repayment "
                                            f"terms templates.\nPlease add the repayment terms "
                                            f"template under a different name."))

    def copy(self, default=None):
        """copy method"""
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _('%s(Copy)', self.name)

        return super().copy(default)
