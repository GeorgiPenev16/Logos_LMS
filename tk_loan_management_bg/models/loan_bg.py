# -*- coding: utf-8 -*-
"""
Разширение на customer.loan за българско законодателство.

Добавя:
- Представляван от (represented_by) — за фирмени кредитополучатели
- Съдлъжници (codebtor_loan_ids) — Many2many с домейн is_codebtor=True
- Поръчители (guarantor_ids) — Many2many с домейн is_guarantor=True
"""
from odoo import fields, models


class CustomerLoanBG(models.Model):
    """Българска локализация на кредит"""
    _inherit = 'customer.loan'

    # ── Представляван от — за фирмени кредитополучатели ──

    represented_by = fields.Many2one(
        comodel_name='res.partner',
        string="Represented By (Представляван от)",
        help="Физическо лице, представляващо фирмата-кредитополучател",
        domain="[('parent_id', '=', customer_id)]",
    )

    # ── Съдлъжници — свързани с конкретен кредит ──

    codebtor_loan_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='customer_loan_codebtor_rel',
        column1='loan_id',
        column2='partner_id',
        string="Co-debtors (Съдлъжници)",
        domain="[('is_codebtor', '=', True)]",
        help="Съдлъжници по този кредит — само партньори с роля 'Съдлъжник'",
    )

    # ── Поръчители — свързани с конкретен кредит ──

    guarantor_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='customer_loan_guarantor_rel',
        column1='loan_id',
        column2='partner_id',
        string="Guarantors (Поръчители)",
        domain="[('is_guarantor', '=', True)]",
        help="Поръчители по този кредит — само партньори с роля 'Поръчител'",
    )
