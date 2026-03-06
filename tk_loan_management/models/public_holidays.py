# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PublicHolidays(models.Model):
    """
    Public holidays
    """
    _name = 'public.holidays'
    _description = __doc__
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title')
    start_date = fields.Date()
    end_date = fields.Date()
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], default='draft', tracking=True)

    @api.constrains('start_date', 'end_date')
    def _validate_dates(self):
        """
        Method to validate that end date is not earlier than start date
        """
        for rec in self:
            start_date, end_date = rec.start_date, rec.end_date,
            if start_date and end_date and end_date < start_date:
                raise ValidationError(_("End date should not be earlier than start date."))

    def action_confirm(self):
        """
        Method to confirm holiday
        """
        for rec in self:
            rec.status = 'confirmed'
        return True
