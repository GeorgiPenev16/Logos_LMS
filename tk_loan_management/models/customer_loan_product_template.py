# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models


class CustomerLoanProductTemplate(models.Model):
    """Customer Loan product template"""
    _inherit = 'product.template'
    _description = __doc__


class CustomerLoanProduct(models.Model):
    """Customer Loan product"""
    _inherit = 'product.product'
    _inherits = {"product.template": "product_tmpl_id"}
