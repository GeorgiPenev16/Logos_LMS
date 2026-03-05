# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from vobject.icalendar import VJournal

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class LoanPayment(models.TransientModel):
    """
    Register loan payment
    """

    def default_get(self, fields):
        """Default get"""
        res = super(LoanPayment, self).default_get(fields)
        loan_id = self.env['customer.loan'].browse(self.env.context.get('active_id'))
        res['customer_loan_id'] = loan_id.id
        res['is_initial_fee_paid'] = loan_id.is_initial_fee_paid
        res['credit_balance'] = loan_id.credit_balance
        res['currency_id'] = loan_id.currency_id
        res['remaining_installment_count'] = loan_id.remain_installment_count
        # res['remain_amount'] = loan_id.remaining_amount
        return res

    _name = 'loan.payment'
    _description = __doc__

    customer_loan_id = fields.Many2one('customer.loan')
    currency_id = fields.Many2one('res.currency')
    amount = fields.Monetary()
    remain_amount = fields.Monetary(compute='_compute_remain_amount')
    date = fields.Date(default=fields.Date.today(), string='Payment Date')
    is_initial_fee_payment = fields.Boolean(default=False)
    initial_fee = fields.Monetary(compute='_compute_initial_fee')
    is_initial_fee_paid = fields.Boolean()
    credit_balance = fields.Monetary()
    remaining_installment_count = fields.Integer()

    @api.depends('customer_loan_id', 'date')
    def _compute_remain_amount(self):
        """
        Method to compute remain amount
        """
        for rec in self:
            remain_amount = 0.0
            date = rec.date
            loan_id = rec.customer_loan_id
            if loan_id:
                for line in loan_id.loan_lines_ids:
                    if line.emi_date <= date:
                        if 'Initial Fee' in line.installments_no and not self.is_initial_fee_paid:
                            fee_per = loan_id.initial_fee_amount
                            fee_amount = fee_per * loan_id.loan_amount / 100
                            amount = line.remaining_amount - fee_amount
                            remain_amount += amount
                        else:
                            remain_amount += line.remaining_amount
            rec.remain_amount = remain_amount

    @api.depends('customer_loan_id', 'is_initial_fee_payment')
    def _compute_initial_fee(self):
        """
        Method to compute customer loan
        """
        for rec in self:
            fee_amount = 0.0
            loan_id = rec.customer_loan_id

            if rec.is_initial_fee_payment and loan_id and loan_id.is_initial_fee:
                fee_per = loan_id.initial_fee_amount
                fee_amount = fee_per * loan_id.loan_amount / 100
            rec.initial_fee = fee_amount

    @api.onchange('is_initial_fee_payment')
    def _onchange_initial_fee_payment(self):
        """
        Method to change amount on changing the
        is initial fee payment
        """
        for rec in self:
            if rec.is_initial_fee_payment:
                rec.amount = rec.initial_fee

    def action_register_payment(self):
        """
        Method to register payment
        """
        amount = self.amount + self.credit_balance
        if self.remaining_installment_count < 2 and amount > self.remain_amount:
            raise ValidationError(
                _("You cannot register a pre-payment that exceeds the remaining principal amount when only one installment with principal is left."))

        date = self.date
        loan_id = self.customer_loan_id

        if self.is_initial_fee_payment:
            amount = self.amount
            if amount != self.initial_fee:
                raise ValidationError(_("Amount should be equal to initial fee"))

            first_ints = loan_id.loan_lines_ids.sorted(key=lambda l: l.emi_date)[0]

            if first_ints.emi_date > fields.Date.today():
                raise ValidationError(
                    _("You can not pay initial fee before first installment date"))

            lines = [
                (0, 0, {
                    'partner_id': loan_id.customer_id.id,
                    'account_id': loan_id.interest_income_account_id.id,
                    'name': "Initial Fee",
                    'credit': amount
                }),
                (0, 0, {
                    'partner_id': loan_id.env.company.partner_id.id,
                    'account_id': loan_id.bank_cash_account.id,
                    'name': "Initial Fee",
                    'debit': amount
                })
            ]
            journal_item_id = loan_id.repayment_journal_item_id
            self._create_journal_entry(journal_item_id, first_ints.installments_no, loan_id,
                                       lines, first_ints, initial_fee=True)
            # loan_id.is_initial_fee_paid = True
        else:
            unpaid_installments = loan_id.loan_lines_ids.filtered(
                lambda line: date >= line.emi_date and line.remaining_amount != 0.0)

            # --- Round 1: Interest ---
            for inst in unpaid_installments:
                if amount <= 0:
                    break
                remaining_interest = inst.interest_amount - inst.paid_interest

                if remaining_interest > 0:
                    pay_interest = min(remaining_interest, amount)

                    lines = [
                        (0, 0, {
                            'partner_id': loan_id.customer_id.id,
                            'account_id': loan_id.interest_income_account_id.id,
                            'name': "Interest Amount",
                            'is_interest': True,
                            'credit': pay_interest
                        }),
                        (0, 0, {
                            'partner_id': loan_id.env.company.partner_id.id,
                            'account_id': loan_id.bank_cash_account.id,
                            'name': "Interest Amount",
                            'is_interest': True,
                            'debit': pay_interest
                        })
                    ]

                    journal_item_id = loan_id.repayment_journal_item_id

                    self._create_journal_entry(journal_item_id, inst.installments_no, loan_id,
                                               lines, inst)
                    inst.paid_interest += pay_interest
                    inst.remaining_amount -= pay_interest
                    amount -= pay_interest

            # --- Round 2: Penalty ---
            for inst in unpaid_installments:
                if amount <= 0:
                    break

                remaining_penalty_interest = inst.penalty_interest - inst.paid_penalty_interest

                if remaining_penalty_interest > 0:
                    pay_amount = min(remaining_penalty_interest, amount)

                    lines = [
                        (0, 0, {
                            'partner_id': loan_id.customer_id.id,
                            'account_id': loan_id.interest_income_account_id.id,
                            'is_overdue_interest': True,
                            'name': "Overdue penalty",
                            'credit': pay_amount
                        }),
                        (0, 0, {
                            'partner_id': loan_id.env.company.partner_id.id,
                            'account_id': loan_id.bank_cash_account.id,
                            'is_overdue_interest': True,
                            'name': "Overdue penalty",
                            'debit': pay_amount
                        })
                    ]
                    journal_item_id = loan_id.repayment_journal_item_id
                    self._create_journal_entry(journal_item_id, inst.installments_no, loan_id,
                                               lines, inst)
                    inst.paid_penalty_interest += pay_amount
                    # inst.remaining_amount -= pay_amount
                    amount -= pay_amount

            # --- Round 3: Fee ---
            for inst in unpaid_installments:
                if amount <= 0:
                    break
                remaining_fee = inst.fee_amount - inst.paid_fee
                if remaining_fee > 0:
                    pay_amount = min(remaining_fee, amount)
                    lines = [
                        (0, 0, {
                            'partner_id': loan_id.customer_id.id,
                            'account_id': loan_id.interest_income_account_id.id,
                            'name': "Monthly Fee",
                            'is_fee': True,
                            'credit': pay_amount
                        }),
                        (0, 0, {
                            'partner_id': loan_id.env.company.partner_id.id,
                            'account_id': loan_id.bank_cash_account.id,
                            'name': "Monthly Fee",
                            'is_fee': True,
                            'debit': pay_amount
                        })
                    ]
                    journal_item_id = loan_id.repayment_journal_item_id
                    self._create_journal_entry(journal_item_id, inst.installments_no, loan_id,
                                               lines, inst)
                    inst.paid_fee += pay_amount
                    # inst.remaining_amount -= pay_amount
                    amount -= pay_amount

            # --- Round 4: Principal
            for inst in unpaid_installments:
                if amount <= 0:
                    break

                remaining_principal = inst.installment_amount - inst.paid_principal

                if remaining_principal > 0:
                    pay_amount = min(remaining_principal, amount)
                    lines = [
                        (0, 0, {
                            'partner_id': loan_id.customer_id.id,
                            'account_id': loan_id.receivable_account_id.id,
                            'name': "Principal Amount",
                            'is_principal': True,
                            'credit': pay_amount
                        }),
                        (0, 0, {
                            'partner_id': loan_id.env.company.partner_id.id,
                            'account_id': loan_id.bank_cash_account.id,
                            'name': "Principal Amount",
                            'is_principal': True,
                            'debit': pay_amount
                        })
                    ]
                    journal_item_id = loan_id.repayment_journal_item_id
                    self._create_journal_entry(journal_item_id, inst.installments_no, loan_id,
                                               lines, inst)
                    inst.paid_principal += pay_amount
                    amount -= pay_amount

            if amount > 0:
                loan_id.credit_balance = amount

    def _create_journal_entry(self, journal_item, ref, loan_id, lines, line_id, initial_fee=False):
        journal_entry_id = self.env['account.move'].create({
            'journal_id': journal_item.id,
            'ref': ref,
            'move_type': 'entry',
            'customer_loan_id': loan_id.id,
            'loan_line_id': line_id.id,
            'is_initial_fee_journal': initial_fee,
            'line_ids': lines
        })
        journal_entry_id.action_post()
