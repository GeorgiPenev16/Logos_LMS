# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models


class CustomerLoanPortalWizardUser(models.TransientModel):
    """Customer Loan Portal Wizard User"""
    _inherit = 'portal.wizard.user'
    _description = __doc__

    def action_grant_access(self):
        """action grant  access"""
        res = super().action_grant_access()
        for rec in self:
            if rec.user_id:
                customer_loan = self.env['customer.loan'].search(
                    [('customer_id', '=', rec.user_id.partner_id.id), ('status', '=', 'confirm')])
                for customer in customer_loan:
                    if not customer.user_id:
                        customer.user_id = rec.user_id
        return res
