# -*- coding: utf-8 -*-
# Copyright 2024-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from datetime import date
from odoo import models, fields, api
from odoo.tools import groupby


class CustomerLoanDashboard(models.Model):
    """Customer Loan Dashboard"""
    _name = "customer.loan.dashboard"
    _description = __doc__

    @api.model
    def get_customer_loan_dashboard(self):
        """Get Customer Loan Dashboard"""
        customer_loans = self.env['customer.loan']

        draft_loans = customer_loans.search_count([('status', '=', 'draft')])
        dept_approval_loans = customer_loans.search_count([('status', '=', 'dept_approval')])
        confirmation_loans = customer_loans.search_count([('status', '=', 'confirmation')])
        disbursement_loans = customer_loans.search_count([('status', '=', 'disbursement')])
        in_progress_loans = customer_loans.search_count([('status', '=', 'in_progress')])
        closure_loans = customer_loans.search_count([('status', '=', 'closure')])
        pre_closure_loans = customer_loans.search_count([('status', '=', 'pre_closure')])
        settlement_loans = customer_loans.search_count([('status', '=', 'settlement')])
        rejected_loans = customer_loans.search_count([('status', '=', 'rejected')])
        cancelled_loans = customer_loans.search_count([('status', '=', 'cancel')])

        data = {
            'draft_loans': draft_loans,
            'dept_approval_loans': dept_approval_loans,
            'confirmation_loans': confirmation_loans,
            'disbursement_loans': disbursement_loans,
            'in_progress_loans': in_progress_loans,
            'closure_loans': closure_loans,
            'pre_closure_loans': pre_closure_loans,
            'settlement_loans': settlement_loans,
            'rejected_loans': rejected_loans,
            'cancelled_loans': cancelled_loans,
            'disbursed_loan_by_month': self._get_disbursed_loan_by_month(),
            'most_selling_loans': self._get_most_selling_loan_type(),
            'loan_details': self._get_total_loan_amount_given_and_recovered(),
            'received_charges': self._get_received_charges_amount(),
            'overdue_installments_loans': self._get_overdue_installments_loans(),
            'overdue_installments_loans_counts': len(self._get_overdue_installments_loans()),
            'unpaid_penalties_loans': self._get_unpaid_penalties_loans(),
            'unpaid_penalties_loans_counts': len(self._get_unpaid_penalties_loans()),
        }
        return data

    def _get_disbursed_loan_by_month(self):
        """Invoiced orders by months"""
        year = date.today().year
        year_str = str(year)
        data_dict = {
            '01/' + year_str: 0,
            '02/' + year_str: 0,
            '03/' + year_str: 0,
            '04/' + year_str: 0,
            '05/' + year_str: 0,
            '06/' + year_str: 0,
            '07/' + year_str: 0,
            '08/' + year_str: 0,
            '09/' + year_str: 0,
            '10/' + year_str: 0,
            '11/' + year_str: 0,
            '12/' + year_str: 0,
        }
        loans = self.env['customer.loan'].search([('journal_entry_id', '!=', False)])
        for data in loans:
            if data.disbursement_date and data.disbursement_date.year == year:
                if data.journal_entry_id.state == 'posted':
                    month_year = data.disbursement_date.strftime("%m/%Y")
                    data_dict[month_year] = data_dict[month_year] + data.loan_amount

        return [list(data_dict.keys()), list(data_dict.values())]

    def _get_most_selling_loan_type(self):
        """Get most selling package"""
        product, qty, data = [], [], []
        loan_types = self.env['customer.loan.type'].search([]).mapped('id')

        most_selling_loan_type_data = self.env['customer.loan']._read_group(
            domain=[
                ('approved_loan_type_id', 'in', loan_types),
                ('status', 'in', ['in_progress', 'closure', 'pre_closure', 'settlement'])
            ],
            groupby=['approved_loan_type_id'],
            aggregates=['id:count'], limit=10)

        for group in most_selling_loan_type_data:
            if group and group[1] > 0:
                product.append(group[0].name)
                qty.append(group[1])

        data = [product, qty]

        return data

    def _get_total_loan_amount_given_and_recovered(self):
        """Get total loan amount given and recovered"""
        loan_detail, amount, data = [], [], []

        given_loan_amount = 0
        recovered_loan_amount = 0
        loans = self.env['customer.loan'].search([('journal_entry_id', '!=', False)])
        for loan in loans:
            if loan.journal_entry_id.state == 'posted':
                given_loan_amount += loan.loan_amount
        loan_detail.append("Loan Amount Given")
        amount.append(round(given_loan_amount, 2))

        for loan in loans:
            if loan.loan_lines_ids:
                for installment in loan.loan_lines_ids:
                    if installment.journal_entry_id and installment.journal_entry_id.state == 'posted':
                        recovered_loan_amount += installment.journal_entry_id.amount_total
                for penalty in loan.penalty_lines_ids:
                    if penalty.journal_entry_id and penalty.journal_entry_id.state == 'posted':
                        recovered_loan_amount += penalty.journal_entry_id.amount_total

        loan_detail.append("Loan Amount Recovered")
        amount.append(round(recovered_loan_amount, 2))

        data = [loan_detail, amount]
        return data

    def _get_received_charges_amount(self):
        """get received charges amount"""
        charges_detail, amount, data = [], [], []

        penalty_amount = 0
        processing_fee_amount = 0
        loans = self.env['customer.loan'].search([('journal_entry_id', '!=', False)])

        for loan in loans:
            if loan.is_processing_fee and loan.journal_entry_id.state == 'posted':
                processing_fee_amount += loan.processing_fee_amount

            if loan.is_penalty:
                for penalty in loan.penalty_lines_ids:
                    if penalty.journal_entry_id and penalty.journal_entry_id.state == 'posted':
                        penalty_amount += penalty.journal_entry_id.amount_total

        charges_detail.append("Penalty Amount")
        amount.append(round(penalty_amount, 2))

        charges_detail.append("Processing fee Amount")
        amount.append(round(processing_fee_amount, 2))

        data = [charges_detail, amount]
        return data

    def _get_overdue_installments_loans(self):
        """Get overdue installments loans"""
        overdue_loan_ids = []
        loans = self.env['customer.loan'].search(
            [('loan_lines_ids', '!=', False), ('status', '=', 'in_progress')])
        for odl in loans:
            for loan in odl.loan_lines_ids:
                if (loan.journal_entry_id and loan.emi_date < fields.Date.today() and
                        loan.journal_entry_id.state != 'posted'):
                    overdue_loan_ids.append(odl.id)

        return list(set(overdue_loan_ids))

    def _get_unpaid_penalties_loans(self):
        """Get unpaid penalties loans"""
        penalty_loan_ids = []
        loans = self.env['customer.loan'].search(
            [('penalty_lines_ids', '!=', False), ('status', '=', 'in_progress'),
             ('is_penalty', '=', True)])
        for pl in loans:
            for penalty in pl.penalty_lines_ids:
                if penalty.journal_entry_id and penalty.journal_entry_id.state != 'posted':
                    penalty_loan_ids.append(pl.id)

        return list(set(penalty_loan_ids))
