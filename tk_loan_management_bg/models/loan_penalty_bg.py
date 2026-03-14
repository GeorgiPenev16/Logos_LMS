# -*- coding: utf-8 -*-
"""
GROUP D — Penalty System (Cash Basis — No Daily GL)

Decision 2026-03-14: Logos uses cash-basis penalty. Account 4961 NOT used.
No journal entries until cash is received. Books stay clean.

Two parts:

1. CustomerLoanLinePenaltyBG — adds 6 penalty fields to customer.loan.lines:
   - penalty_start_date        computed: emi_date + lms_penalty_grace_days
   - penalty_accrued_informational  daily cron display-only amount (no GL)
   - penalty_calculated_at_payment  fresh calc when payment wizard opens
   - penalty_custom_amount          staff-negotiated override (Option 3)
   - waive_penalty                  permanent waiver flag (Option 2)
   - paid_penalty                   running total actually received (posted)

2. CustomerLoanPenaltyBG — overrides base GL-posting penalty crons:
   - _cron_installment_due_penalty()  → no-op (base posts DR/CR — wrong for Logos)
   - _cron_loan_overdue_penalty()     → no-op (compound interest — wrong)
   - _cron_update_penalty_informational() → our informational-only daily update

Formula (informational display, zero accounting impact):
    daily_rate   = lms_penalty_rate_annual / 100 / lms_penalty_divisor
    overdue_days = max(0, today − penalty_start_date)
    penalty      = (remaining_principal + remaining_interest) × daily_rate × overdue_days
"""
from datetime import timedelta
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class CustomerLoanLinePenaltyBG(models.Model):
    """Penalty tracking fields on installment lines."""
    _inherit = 'customer.loan.lines'

    # ── penalty_start_date ────────────────────────────────────────────────
    penalty_start_date = fields.Date(
        string='Penalty Start / Начало наказателна лихва',
        compute='_compute_penalty_start_date',
        store=True,
        readonly=True,
        help='Penalty starts accruing from this date (emi_date + grace days from Settings).',
    )

    # ── informational running total (no GL) ──────────────────────────────
    penalty_accrued_informational = fields.Float(
        string='Accrued Penalty (Info) / Наказателна лихва (информ.)',
        digits=(16, 2),
        default=0.0,
        help='Updated daily by cron — display only. Zero accounting impact. '
             'Shown to staff and on client statement.',
    )

    # ── recalculated fresh when wizard opens ─────────────────────────────
    penalty_calculated_at_payment = fields.Float(
        string='Penalty at Payment Date / Наказателна лихва към плащане',
        digits=(16, 2),
        default=0.0,
        help='Recalculated fresh on payment_date when payment wizard opens. '
             'Default amount for Option 1 (full penalty).',
    )

    # ── staff-negotiated custom amount (Option 3) ─────────────────────────
    penalty_custom_amount = fields.Float(
        string='Custom Penalty / Договорена наказателна лихва',
        digits=(16, 2),
        default=0.0,
        help='Staff-editable negotiated amount. Must be ≥ 0 and ≤ penalty_calculated_at_payment.',
    )

    # ── permanent waiver flag (Option 2) ─────────────────────────────────
    waive_penalty = fields.Boolean(
        string='Waive Penalty / Опрости наказателна лихва',
        default=False,
        help='When checked, penalty is excluded from this installment permanently. '
             'penalty_accrued_informational is reset to 0.',
    )

    # ── cumulative penalty cash received ─────────────────────────────────
    paid_penalty = fields.Float(
        string='Paid Penalty / Платена наказателна лихва',
        digits=(16, 2),
        default=0.0,
        readonly=True,
        help='Running total of penalty received and posted (DR 5031 / CR 7230). '
             'Updated by payment wizard after each payment.',
    )

    # ── compute ──────────────────────────────────────────────────────────

    @api.depends('emi_date', 'company_id.lms_penalty_grace_days')
    def _compute_penalty_start_date(self):
        for line in self:
            if line.emi_date:
                grace = (line.company_id.lms_penalty_grace_days or 0)
                line.penalty_start_date = line.emi_date + timedelta(days=grace)
            else:
                line.penalty_start_date = False


class CustomerLoanPenaltyBG(models.Model):
    """Override base penalty crons + add informational-only daily update."""
    _inherit = 'customer.loan'

    # ── Neutralise base GL-posting crons ─────────────────────────────────

    @api.model
    def _cron_installment_due_penalty(self):
        """Override: suppress base GL penalty posting (wrong for Logos cash-basis).

        Base method creates DR bank / CR penalty journal entries daily.
        Logos posts penalty only on cash receipt (DR 5031 / CR 7230 in wizard).
        Informational amounts are updated by _cron_update_penalty_informational().
        """
        return True  # intentional no-op

    @api.model
    def _cron_loan_overdue_penalty(self):
        """Override: suppress base compound overdue penalty posting (wrong for Logos)."""
        return True  # intentional no-op

    # ── Informational-only daily cron ────────────────────────────────────

    @api.model
    def _cron_update_penalty_informational(self):
        """Daily cron — update penalty_accrued_informational. ZERO journal entries.

        For each overdue installment (emi_date < today, not waived, not fully paid):
            daily_rate   = lms_penalty_rate_annual / 100 / lms_penalty_divisor
            overdue_days = max(0, today − penalty_start_date)
            penalty      = (remaining_principal + remaining_interest)
                           × daily_rate × overdue_days

        Resets informational to 0 for waived or fully-paid lines.
        No DR/CR anywhere. Account 4961 NOT used.
        """
        today = fields.Date.today()
        company = self.env.company

        rate_annual = company.lms_penalty_rate_annual or 0.0
        divisor = company.lms_penalty_divisor or 360

        if not rate_annual:
            _logger.warning(
                'LMS penalty informational cron: lms_penalty_rate_annual = 0. Skipping.')
            return

        daily_rate = rate_annual / 100.0 / divisor
        loans = self.search([('status', '=', 'in_progress')])
        updated = 0

        for loan in loans:
            for line in loan.loan_lines_ids:
                if line.display_type:
                    continue

                # Lines to reset: waived or fully cleared
                unpaid_base = (line.remaining_principal or 0.0) + (line.remaining_interest or 0.0)
                if line.waive_penalty or unpaid_base <= 0:
                    if line.penalty_accrued_informational != 0.0:
                        line.penalty_accrued_informational = 0.0
                    continue

                # Only overdue lines (past penalty_start_date)
                start = line.penalty_start_date
                if not start or today <= start:
                    if line.penalty_accrued_informational != 0.0:
                        line.penalty_accrued_informational = 0.0
                    continue

                overdue_days = (today - start).days
                line.penalty_accrued_informational = round(
                    unpaid_base * daily_rate * overdue_days, 2
                )
                updated += 1

        _logger.info(
            'LMS penalty informational cron: %d lines updated for %s', updated, today)
