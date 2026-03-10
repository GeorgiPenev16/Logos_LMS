# -*- coding: utf-8 -*-
"""
Разширение на customer.loan за българско законодателство.

Добавя:
- Представляван от (represented_by) — за фирмени кредитополучатели
- Съдлъжници (codebtor_loan_ids) — Many2many с домейн is_codebtor=True
- Поръчители (guarantor_ids) — Many2many с домейн is_guarantor=True
"""
from odoo import fields, models, api


class CustomerLoanBG(models.Model):
    """Българска локализация на кредит"""
    _inherit = 'customer.loan'

    # ── Представляван от — за фирмени кредитополучатели ──

    represented_by = fields.Many2one(
        comodel_name='res.partner',
        string="Represented By / Представляван от",
        help="Individual representing the company borrower (МОЛ)",
        domain="[('is_company', '=', False)]",
    )

    @api.onchange('customer_id')
    def _onchange_customer_id_represented_by(self):
        """Auto-populate represented_by from the company's МОЛ (manager_id)."""
        if self.customer_id and self.customer_id.is_company:
            self.represented_by = self.customer_id.manager_id or False
        else:
            self.represented_by = False

    # ── Co-debtors — linked to specific loan ──

    codebtor_loan_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='customer_loan_codebtor_rel',
        column1='loan_id',
        column2='partner_id',
        string="Co-debtors / Съдлъжници",
        domain="[('is_codebtor', '=', True)]",
        help="Co-debtors on this loan — only partners with Co-debtor role",
    )

    # ── Guarantors — linked to specific loan ──

    guarantor_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='customer_loan_guarantor_rel',
        column1='loan_id',
        column2='partner_id',
        string="Guarantors / Поръчители",
        domain="[('is_guarantor', '=', True)]",
        help="Guarantors on this loan — only partners with Guarantor role",
    )
