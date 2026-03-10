# -*- coding: utf-8 -*-
"""
Phase 5 — Loan Document Template model.

Stores editable HTML templates with Bulgarian placeholder syntax.
Templates are rendered at generation time by substituting all
{placeholder} tokens with live data from the loan record.
"""
from odoo import fields, models


class LoanDocumentTemplate(models.Model):
    """Шаблон за генериране на документи към кредит."""

    _name = 'loan.document.template'
    _description = 'Loan Document Template / Шаблон за документ'
    _order = 'document_type, name'
    _rec_name = 'name'

    name = fields.Char(
        string="Template Name / Наименование",
        required=True,
    )

    document_type = fields.Selection(
        selection=[
            ('contract',   'Договор за кредит'),
            ('aml',        'Декларация ЗМИП/AML'),
            ('promissory', 'Запис на заповед'),
            ('sef',        'СЕФ'),
            ('receipt',    'Разписка'),
            ('annex',      'Анекс'),
            ('other',      'Друго'),
        ],
        string="Document Type / Вид документ",
        required=True,
        default='other',
    )

    content = fields.Html(
        string="Content / Съдържание",
        sanitize=False,
        help=(
            "HTML template with {placeholder} tokens.\n\n"
            "LOAN:  {loan_ref}  {loan_date}  {loan_amount}  {loan_amount_words}\n"
            "       {interest_rate}  {gpr}  {term}  {monthly_payment}\n"
            "       {total_payable}  {total_cost}  {start_date}\n\n"
            "BORROWER:  {borrower_name}  {borrower_egn}  {borrower_eik}  {borrower_address}\n"
            "           {represented_by}  {represented_egn}\n\n"
            "GUARANTORS: {guarantor_1_name}  {guarantor_1_egn}\n"
            "            {codebtor_1_name}   {codebtor_1_egn}\n\n"
            "COMPANY:  {company_name}  {company_eik}  {company_address}\n"
            "          {company_mol}  {city}  {today_date}"
        ),
    )

    is_active = fields.Boolean(
        string="Active / Активен",
        default=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company / Компания",
        default=lambda self: self.env.company,
    )
