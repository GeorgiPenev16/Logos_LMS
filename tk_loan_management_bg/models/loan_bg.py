# -*- coding: utf-8 -*-
"""
Разширение на customer.loan за българско законодателство.

Добавя:
- Представляван от (represented_by) — за фирмени кредитополучатели
- Редове на съдлъжници (codebtor_line_ids) — с % на съдлъжничество
- Редове на поръчители (guarantor_line_ids) — с % на поръчителство
"""
from odoo import fields, models, api


class CustomerLoanCodbtorLine(models.Model):
    """Ред на съдлъжник към кредит"""
    _name = 'customer.loan.codebtor.line'
    _description = 'Loan Co-debtor Line / Ред на съдлъжник'

    loan_id = fields.Many2one(
        comodel_name='customer.loan',
        string="Loan / Кредит",
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Co-debtor / Съдлъжник",
        required=True,
        domain="[('is_codebtor', '=', True)]",
    )
    guarantee_percentage = fields.Float(
        string="Share % / % Съдлъжничество",
        default=100.0,
        digits=(5, 2),
        help="Percentage of the loan this co-debtor is responsible for",
    )


class CustomerLoanGuarantorLine(models.Model):
    """Ред на поръчител към кредит"""
    _name = 'customer.loan.guarantor.line'
    _description = 'Loan Guarantor Line / Ред на поръчител'

    loan_id = fields.Many2one(
        comodel_name='customer.loan',
        string="Loan / Кредит",
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Guarantor / Поръчител",
        required=True,
        domain="[('is_guarantor', '=', True)]",
    )
    guarantee_percentage = fields.Float(
        string="Guarantee % / % Поръчителство",
        default=100.0,
        digits=(5, 2),
        help="Percentage of the loan covered by this guarantor",
    )


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

    # ── Co-debtor lines — one row per co-debtor with percentage ──

    codebtor_line_ids = fields.One2many(
        comodel_name='customer.loan.codebtor.line',
        inverse_name='loan_id',
        string="Co-debtors / Съдлъжници",
    )

    # ── Guarantor lines — one row per guarantor with percentage ──

    guarantor_line_ids = fields.One2many(
        comodel_name='customer.loan.guarantor.line',
        inverse_name='loan_id',
        string="Guarantors / Поръчители",
    )
