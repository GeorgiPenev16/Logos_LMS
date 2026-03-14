# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompanyLMSBG(models.Model):
    """Bulgarian LMS configuration fields stored on res.company."""
    _inherit = 'res.company'

    # ── Penalty configuration ─────────────────────────────────────────────
    lms_penalty_rate_annual = fields.Float(
        string='Penalty Rate Annual (%)',
        default=10.15,
        digits=(5, 4),
        help='Annual penalty interest rate per ЗПК Art. 33 / Постановление №426/2014. '
             'Default: ECB base rate + 8pp = 10.15%',
    )
    lms_penalty_divisor = fields.Integer(
        string='Penalty Divisor (days/year)',
        default=360,
        help='Divisor for daily penalty calculation. Typically 360 (per BNB convention).',
    )
    lms_penalty_grace_days = fields.Integer(
        string='Penalty Grace Days',
        default=0,
        help='Number of overdue days before penalty starts accruing.',
    )

    # ── Invoice mode ──────────────────────────────────────────────────────
    lms_fee_invoice_on_disburse = fields.Boolean(
        string='Issue Fee Invoice on Disbursement',
        default=True,
        help='When enabled, a customer invoice is created for origination fees at disbursement.',
    )

    # ── Journals ─────────────────────────────────────────────────────────
    lms_disbursement_journal_id = fields.Many2one(
        'account.journal',
        string='Disbursement Journal',
        domain=[('type', '=', 'bank')],
        help='Bank journal used for loan disbursements (LOAN-DISB).',
    )
    lms_collection_journal_id = fields.Many2one(
        'account.journal',
        string='Collection Journal',
        domain=[('type', '=', 'bank')],
        help='Bank journal used for loan repayment collections (LOAN-COL).',
    )
    lms_operations_journal_id = fields.Many2one(
        'account.journal',
        string='Operations Journal',
        domain=[('type', '=', 'general')],
        help='General journal for interest accruals, reclassifications, provisions (LOAN-OPS).',
    )
    lms_invoice_journal_id = fields.Many2one(
        'account.journal',
        string='Fee Invoice Journal',
        domain=[('type', '=', 'sale')],
        help='Sales journal for origination fee invoices (LOAN-INV).',
    )

    # ── Asset / Receivable accounts ───────────────────────────────────────
    lms_lt_loan_account_id = fields.Many2one(
        'account.account',
        string='LT Loan Account (262)',
        help='Long-term loan receivable — НСС account 262.',
    )
    lms_st_loan_account_id = fields.Many2one(
        'account.account',
        string='ST Loan Account (4110)',
        help='Short-term loan receivable (current portion ≤12 months) — НСС account 4110.',
    )
    lms_overdue_loan_account_id = fields.Many2one(
        'account.account',
        string='Overdue Loan Account (4112)',
        help='Overdue principal receivable — НСС account 4112.',
    )
    lms_fees_receivable_account_id = fields.Many2one(
        'account.account',
        string='Fees Receivable Account (4113)',
        help='Fees receivable — НСС account 4113.',
    )
    lms_accrued_interest_account_id = fields.Many2one(
        'account.account',
        string='Accrued Interest Account (4960)',
        help='Accrued interest receivable — НСС account 4960.',
    )
    lms_allowance_account_id = fields.Many2one(
        'account.account',
        string='Loan Loss Allowance Account (2991)',
        help='Provision / allowance for loan losses — НСС account 2991.',
    )

    # ── Income accounts ───────────────────────────────────────────────────
    lms_interest_income_account_id = fields.Many2one(
        'account.account',
        string='Interest Income Account (7210)',
        help='Interest income on loans — НСС account 7210.',
    )
    lms_fee_income_account_id = fields.Many2one(
        'account.account',
        string='Fee Income Account (7220)',
        help='Origination fee income — НСС account 7220.',
    )
    lms_penalty_income_account_id = fields.Many2one(
        'account.account',
        string='Penalty Income Account (7230)',
        help='Penalty interest income (cash basis) — НСС account 7230.',
    )
    lms_early_repayment_income_account_id = fields.Many2one(
        'account.account',
        string='Early Repayment Fee Income (7240)',
        help='Income from early repayment fees — НСС account 7240.',
    )
    lms_other_income_account_id = fields.Many2one(
        'account.account',
        string='Other LMS Income Account (7250)',
        help='Other loan-related income — НСС account 7250.',
    )

    # ── Expense accounts ──────────────────────────────────────────────────
    lms_provision_expense_account_id = fields.Many2one(
        'account.account',
        string='Provision Expense Account (6290)',
        help='Expense for loan loss provisions — НСС account 6290.',
    )


class ResConfigSettingsLMSBG(models.TransientModel):
    """Expose LMS accounting config in Settings → Accounting → Loans (БГ)."""
    _inherit = 'res.config.settings'

    # ── Penalty ───────────────────────────────────────────────────────────
    lms_penalty_rate_annual = fields.Float(
        related='company_id.lms_penalty_rate_annual',
        readonly=False,
        string='Penalty Rate Annual (%)',
    )
    lms_penalty_divisor = fields.Integer(
        related='company_id.lms_penalty_divisor',
        readonly=False,
        string='Penalty Divisor (days/year)',
    )
    lms_penalty_grace_days = fields.Integer(
        related='company_id.lms_penalty_grace_days',
        readonly=False,
        string='Penalty Grace Days',
    )

    # ── Invoice mode ──────────────────────────────────────────────────────
    lms_fee_invoice_on_disburse = fields.Boolean(
        related='company_id.lms_fee_invoice_on_disburse',
        readonly=False,
        string='Issue Fee Invoice on Disbursement',
    )

    # ── Journals ─────────────────────────────────────────────────────────
    lms_disbursement_journal_id = fields.Many2one(
        related='company_id.lms_disbursement_journal_id',
        readonly=False,
        string='Disbursement Journal',
    )
    lms_collection_journal_id = fields.Many2one(
        related='company_id.lms_collection_journal_id',
        readonly=False,
        string='Collection Journal',
    )
    lms_operations_journal_id = fields.Many2one(
        related='company_id.lms_operations_journal_id',
        readonly=False,
        string='Operations Journal',
    )
    lms_invoice_journal_id = fields.Many2one(
        related='company_id.lms_invoice_journal_id',
        readonly=False,
        string='Fee Invoice Journal',
    )

    # ── Asset / Receivable accounts ───────────────────────────────────────
    lms_lt_loan_account_id = fields.Many2one(
        related='company_id.lms_lt_loan_account_id',
        readonly=False,
        string='LT Loan Account (262)',
    )
    lms_st_loan_account_id = fields.Many2one(
        related='company_id.lms_st_loan_account_id',
        readonly=False,
        string='ST Loan Account (4110)',
    )
    lms_overdue_loan_account_id = fields.Many2one(
        related='company_id.lms_overdue_loan_account_id',
        readonly=False,
        string='Overdue Loan Account (4112)',
    )
    lms_fees_receivable_account_id = fields.Many2one(
        related='company_id.lms_fees_receivable_account_id',
        readonly=False,
        string='Fees Receivable Account (4113)',
    )
    lms_accrued_interest_account_id = fields.Many2one(
        related='company_id.lms_accrued_interest_account_id',
        readonly=False,
        string='Accrued Interest Account (4960)',
    )
    lms_allowance_account_id = fields.Many2one(
        related='company_id.lms_allowance_account_id',
        readonly=False,
        string='Loan Loss Allowance Account (2991)',
    )

    # ── Income accounts ───────────────────────────────────────────────────
    lms_interest_income_account_id = fields.Many2one(
        related='company_id.lms_interest_income_account_id',
        readonly=False,
        string='Interest Income Account (7210)',
    )
    lms_fee_income_account_id = fields.Many2one(
        related='company_id.lms_fee_income_account_id',
        readonly=False,
        string='Fee Income Account (7220)',
    )
    lms_penalty_income_account_id = fields.Many2one(
        related='company_id.lms_penalty_income_account_id',
        readonly=False,
        string='Penalty Income Account (7230)',
    )
    lms_early_repayment_income_account_id = fields.Many2one(
        related='company_id.lms_early_repayment_income_account_id',
        readonly=False,
        string='Early Repayment Fee Income (7240)',
    )
    lms_other_income_account_id = fields.Many2one(
        related='company_id.lms_other_income_account_id',
        readonly=False,
        string='Other LMS Income Account (7250)',
    )

    # ── Expense accounts ──────────────────────────────────────────────────
    lms_provision_expense_account_id = fields.Many2one(
        related='company_id.lms_provision_expense_account_id',
        readonly=False,
        string='Provision Expense Account (6290)',
    )
