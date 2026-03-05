# -*- coding: utf-8 -*-
# Copyright 2024 - Today Techkhedut.
# Part of Techkhedut. See LICENSE file for full copyright and licensing detail
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CustomerCollateralType(models.Model):
    """Customer Collateral Type"""
    _name = 'customer.collateral.type'
    _description = __doc__

    name = fields.Char(required=True)

    @api.constrains('name')
    def _check_name(self):
        """check name"""
        for rec in self:
            names = self.search([('id', '!=', rec.id)])
            for name in names:
                if rec.name == name.name:
                    raise ValidationError(_("This collateral type already exists."))

    def copy(self, default=None):
        """copy method"""
        if default is None:
            default = {}

        if not default.get('name'):
            default['name'] = _('%s (copy)', self.name)
        return super().copy(default)
